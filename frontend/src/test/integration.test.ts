/**
 * integration.test.ts
 *
 * End-to-end flow tests: simulates the full lifecycle of a user session,
 * from uploading a screenshot, receiving streaming events via WebSocket,
 * to verifying that the Zustand stores reflect the correct final state.
 *
 * No real network connections are made; fetch and WebSocket are mocked.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useChatStore } from '@/store/useChatStore';
import { useDiffStore } from '@/store/useDiffStore';
import { useFileStore } from '@/store/useFileStore';
import { useGitStore } from '@/store/useGitStore';
import { wsClient } from '@/api/ws';
import { uploadScreenshot } from '@/api/rest';

// ── WebSocket mock ──────────────────────────────────────────────────────────

class MockWebSocket {
  static OPEN = 1;
  onopen: () => void = () => {};
  onmessage: (e: { data: string }) => void = () => {};
  onclose: () => void = () => {};
  onerror: (e: unknown) => void = () => {};
  send = vi.fn();
  close = vi.fn();
  readyState = 0;
}
globalThis.WebSocket = MockWebSocket as any;
window.WebSocket = MockWebSocket as any;

// ── Fetch mock ───────────────────────────────────────────────────────────────

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// ── Workspace API mock (used by file/git stores) ─────────────────────────────

vi.mock('@/api/workspace', () => ({
  getFiles: vi.fn(async () => [
    { name: 'index.html', path: 'index.html', isDir: false },
    { name: 'style.css',  path: 'style.css',  isDir: false },
  ]),
  getFile: vi.fn(async (_sid: string, path: string) =>
    path === 'index.html' ? '<html></html>' : 'body { color: red; }'
  ),
  writeFile: vi.fn(async () => {}),
  getGitLog: vi.fn(async () => [
    { hash: 'a1b2c3d', message: 'AI: generate index.html', date: '2026-05-16' },
  ]),
  getGitStatus: vi.fn(async () => ''),
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function resetStores() {
  useChatStore.setState({ sessionId: null, messages: [], connectionStatus: 'disconnected' });
  useDiffStore.setState({ pendingDiffs: [] });
  useFileStore.setState({ files: [], activeFilePath: null, activeFileContent: '', isLoading: false });
  useGitStore.setState({ commits: [], statusText: '', isLoading: false });
  wsClient.disconnect();
}

function getWs() {
  return (wsClient as any).ws as MockWebSocket;
}

function emit(ws: MockWebSocket, event: object) {
  ws.onmessage({ data: JSON.stringify(event) });
}

// ────────────────────────────────────────────────────────────────────────────

describe('Integration: Full Session Lifecycle', () => {
  beforeEach(() => resetStores());

  it('connects WebSocket and marks store as connected', () => {
    wsClient.connect('sess-1');
    const ws = getWs();
    ws.readyState = MockWebSocket.OPEN;
    ws.onopen();
    expect(useChatStore.getState().connectionStatus).toBe('connected');
  });

  it('streams tokens token-by-token into the last assistant message', () => {
    useChatStore.getState().prepareAssistantMessage();
    wsClient.connect('sess-1');
    const ws = getWs();

    emit(ws, { type: 'token', data: 'Hello' });
    emit(ws, { type: 'token', data: ', world' });
    emit(ws, { type: 'token', data: '!' });

    const msgs = useChatStore.getState().messages;
    expect(msgs[msgs.length - 1].content).toBe('Hello, world!');
  });

  it('finalizes message (isStreaming=false) on "done" event', () => {
    useChatStore.getState().prepareAssistantMessage();
    wsClient.connect('sess-1');
    const ws = getWs();

    emit(ws, { type: 'token', data: 'Some code' });
    emit(ws, { type: 'done' });

    const msgs = useChatStore.getState().messages;
    expect(msgs[msgs.length - 1].isStreaming).toBe(false);
    expect(msgs[msgs.length - 1].content).toBe('Some code');
  });

  it('registers tool calls in the assistant message', () => {
    useChatStore.getState().prepareAssistantMessage();
    wsClient.connect('sess-1');
    const ws = getWs();

    emit(ws, { type: 'tool_call', data: { name: 'create_file', arguments: { path: 'index.html', content: '<h1>' } } });

    const msgs = useChatStore.getState().messages;
    const last = msgs[msgs.length - 1];
    expect(last.toolCalls).toHaveLength(1);
    expect(last.toolCalls![0].name).toBe('create_file');
  });

  it('adds a pending diff to diffStore when tool_result contains diff data', () => {
    useChatStore.getState().prepareAssistantMessage();
    wsClient.connect('sess-1');
    const ws = getWs();

    emit(ws, {
      type: 'tool_result',
      data: {
        tool_name: 'generate_diff',
        success: true,
        output: '',
        data: {
          path: 'index.html',
          old_content: '<h1>Old</h1>',
          new_content: '<h1>New</h1>',
          diff: '--- a/index.html\n+++ b/index.html',
        },
      },
    });

    const diffs = useDiffStore.getState().pendingDiffs;
    expect(diffs).toHaveLength(1);
    expect(diffs[0].path).toBe('index.html');
    expect(diffs[0].newContent).toBe('<h1>New</h1>');
    expect(diffs[0].status).toBe('pending');
  });

  it('removes diff from pending list after acceptance', () => {
    useDiffStore.getState().addPendingDiff({
      path: 'style.css',
      oldContent: 'body {}',
      newContent: 'body { color: red; }',
      diffText: '...',
      status: 'pending',
    });
    useDiffStore.getState().resolveDiff('style.css', 'accepted');
    expect(useDiffStore.getState().pendingDiffs).toHaveLength(0);
  });

  it('removes diff from pending list after rejection', () => {
    useDiffStore.getState().addPendingDiff({
      path: 'app.js',
      oldContent: '',
      newContent: 'alert("hi")',
      diffText: '...',
      status: 'pending',
    });
    useDiffStore.getState().resolveDiff('app.js', 'rejected');
    expect(useDiffStore.getState().pendingDiffs).toHaveLength(0);
  });

  it('populates file store after session starts', async () => {
    await useFileStore.getState().refreshFiles('sess-1');
    const { files } = useFileStore.getState();
    expect(files).toHaveLength(2);
    expect(files.map(f => f.name)).toContain('index.html');
    expect(files.map(f => f.name)).toContain('style.css');
  });

  it('loads file content into editor store', async () => {
    await useFileStore.getState().openFile('sess-1', 'index.html');
    const { activeFilePath, activeFileContent } = useFileStore.getState();
    expect(activeFilePath).toBe('index.html');
    expect(activeFileContent).toBe('<html></html>');
  });

  it('loads git commits after generation', async () => {
    await useGitStore.getState().refreshGit('sess-1');
    const { commits } = useGitStore.getState();
    expect(commits).toHaveLength(1);
    expect(commits[0].hash).toBe('a1b2c3d');
    expect(commits[0].message).toBe('AI: generate index.html');
  });

  it('sends user feedback over WebSocket and creates placeholder message', () => {
    wsClient.connect('sess-1');
    const ws = getWs();
    ws.readyState = MockWebSocket.OPEN;
    ws.onopen();

    wsClient.sendFeedback('Change the font to blue');

    expect(ws.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'feedback', content: 'Change the font to blue' })
    );

    const msgs = useChatStore.getState().messages;
    const userMsg = msgs.find(m => m.role === 'user' && m.content === 'Change the font to blue');
    expect(userMsg).toBeDefined();
  });
});

// ────────────────────────────────────────────────────────────────────────────

describe('Integration: Upload → SSE stream → Session ID', () => {
  beforeEach(() => {
    resetStores();
    mockFetch.mockReset();
  });

  it('uploadScreenshot sends file and returns a streamable Response', async () => {
    const file = new File(['img-data'], 'design.png', { type: 'image/png' });
    const mockResponse = { ok: true, body: 'stream' };
    mockFetch.mockResolvedValueOnce(mockResponse);

    const res = await uploadScreenshot(file, 'react', false);

    expect(res).toBe(mockResponse);
    expect(mockFetch).toHaveBeenCalledOnce();

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v1/design/upload');

    const fd: FormData = opts.body;
    expect(fd.get('framework')).toBe('react');
    expect(fd.get('file')).toBe(file);
  });

  it('handles network-level failure without crashing', async () => {
    const file = new File([], 'x.png');
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    await expect(uploadScreenshot(file)).rejects.toThrow('Network error');
  });
});
