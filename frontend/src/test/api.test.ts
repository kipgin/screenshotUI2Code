/**
 * api.test.ts
 *
 * Tests covering:
 *  - Correct HTTP method, URL, and body for each API call
 *  - Successful response parsing (shape of returned data)
 *  - HTTP-error handling (non-ok responses)
 *  - FormData contents for multipart endpoints
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getFiles, getFile, writeFile, getGitLog, getGitStatus } from '@/api/workspace';
import { uploadScreenshot, submitFeedback, getSession } from '@/api/rest';
import type { FileNode, GitCommit } from '@/types';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

describe('REST – workspace.ts', () => {
  beforeEach(() => mockFetch.mockReset());

  // ── getFiles ────────────────────────────────────────────────────────────

  describe('getFiles()', () => {
    const mockTree: FileNode[] = [
      { name: 'index.html', path: 'index.html', isDir: false },
      { name: 'src',        path: 'src',         isDir: true, children: [] },
    ];

    it('builds the correct URL for the root path', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockTree });
      await getFiles('sess-1', '.');
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/workspace/sess-1/files?path=.');
    });

    it('URL-encodes a nested sub-path', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => [] });
      await getFiles('sess-1', 'src/components');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/workspace/sess-1/files?path=src%2Fcomponents'
      );
    });

    it('returns the parsed file tree', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockTree });
      const result = await getFiles('sess-1');
      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('index.html');
      expect(result[1].isDir).toBe(true);
    });

    it('throws on non-ok HTTP response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(getFiles('bad-sess')).rejects.toThrow('Failed to get files');
    });
  });

  // ── getFile ─────────────────────────────────────────────────────────────

  describe('getFile()', () => {
    it('returns the content string from the response body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ content: '<h1>Hello World</h1>' }),
      });
      const content = await getFile('sess-1', 'index.html');
      expect(content).toBe('<h1>Hello World</h1>');
    });

    it('throws when the file is not found (404)', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(getFile('sess-1', 'missing.js')).rejects.toThrow('Failed to read file');
    });
  });

  // ── writeFile ────────────────────────────────────────────────────────────

  describe('writeFile()', () => {
    it('sends POST with JSON body containing path and content', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
      await writeFile('sess-1', 'src/app.ts', 'console.log("hi")');

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/workspace/sess-1/file');
      expect(init.method).toBe('POST');
      expect(init.headers['Content-Type']).toBe('application/json');

      const body = JSON.parse(init.body);
      expect(body.path).toBe('src/app.ts');
      expect(body.content).toBe('console.log("hi")');
    });

    it('throws on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(writeFile('sess-1', 'bad.ts', '')).rejects.toThrow('Failed to write file');
    });
  });

  // ── getGitLog ────────────────────────────────────────────────────────────

  describe('getGitLog()', () => {
    const mockCommits: GitCommit[] = [
      { hash: 'abc1234', message: 'Initial commit', date: '2026-05-01' },
      { hash: 'def5678', message: 'Add CSS styling' },
    ];

    it('returns commit array from response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockCommits });
      const commits = await getGitLog('sess-1');
      expect(commits).toHaveLength(2);
      expect(commits[0].hash).toBe('abc1234');
      expect(commits[1].message).toBe('Add CSS styling');
    });

    it('returns empty array on non-ok response (graceful degradation)', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      const commits = await getGitLog('sess-1');
      expect(commits).toEqual([]);
    });
  });

  // ── getGitStatus ─────────────────────────────────────────────────────────

  describe('getGitStatus()', () => {
    it('returns the status string', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'M index.html' }) });
      const status = await getGitStatus('sess-1');
      expect(status).toBe('M index.html');
    });

    it('returns empty string when the response has no status field', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
      expect(await getGitStatus('sess-1')).toBe('');
    });

    it('returns empty string on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      expect(await getGitStatus('sess-1')).toBe('');
    });
  });
});

// ────────────────────────────────────────────────────────────────────────────
// REST – rest.ts (design endpoints)
// ────────────────────────────────────────────────────────────────────────────

describe('REST – rest.ts', () => {
  beforeEach(() => mockFetch.mockReset());

  // ── uploadScreenshot ────────────────────────────────────────────────────

  describe('uploadScreenshot()', () => {
    it('sends to the correct endpoint with POST', async () => {
      const file = new File(['dummy'], 'design.png', { type: 'image/png' });
      mockFetch.mockResolvedValueOnce({ ok: true });
      await uploadScreenshot(file);
      expect(mockFetch.mock.calls[0][0]).toBe('/api/v1/design/upload');
      expect(mockFetch.mock.calls[0][1].method).toBe('POST');
    });

    it('includes the file in FormData', async () => {
      const file = new File(['px'], 'shot.png', { type: 'image/png' });
      mockFetch.mockResolvedValueOnce({ ok: true });
      await uploadScreenshot(file, 'react', true);

      const body: FormData = mockFetch.mock.calls[0][1].body;
      expect(body instanceof FormData).toBe(true);
      expect(body.get('file')).toBe(file);
      expect(body.get('framework')).toBe('react');
      expect(body.get('enable_parallel')).toBe('true');
    });

    it('passes enable_parallel=false when disabled', async () => {
      const file = new File([''], 'shot.png');
      mockFetch.mockResolvedValueOnce({ ok: true });
      await uploadScreenshot(file, 'html/css', false);

      const body: FormData = mockFetch.mock.calls[0][1].body;
      expect(body.get('enable_parallel')).toBe('false');
    });
  });

  // ── submitFeedback ───────────────────────────────────────────────────────

  describe('submitFeedback()', () => {
    it('POSTs to /design/feedback with session_id and feedback in FormData', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await submitFeedback('sess-xyz', 'Make the button blue');

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe('/api/v1/design/feedback');
      expect(init.method).toBe('POST');

      const body: FormData = init.body;
      expect(body.get('session_id')).toBe('sess-xyz');
      expect(body.get('feedback')).toBe('Make the button blue');
    });
  });

  // ── getSession ───────────────────────────────────────────────────────────

  describe('getSession()', () => {
    const mockSession = {
      session_id: 'sess-abc',
      framework: 'react',
      workspace: '/workspaces/sess-abc',
      message_count: 5,
      token_count: 1024,
    };

    it('fetches session metadata and returns the parsed object', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockSession });
      const session = await getSession('sess-abc');
      expect(session.session_id).toBe('sess-abc');
      expect(session.framework).toBe('react');
      expect(session.message_count).toBe(5);
      expect(session.token_count).toBe(1024);
    });

    it('throws "Session not found" on 404', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(getSession('missing')).rejects.toThrow('Session not found');
    });
  });
});
