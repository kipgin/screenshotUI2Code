import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from '@/store/useChatStore';
import { useDiffStore } from '@/store/useDiffStore';
import { useFileStore } from '@/store/useFileStore';
import { useGitStore } from '@/store/useGitStore';

// Mock the workspace APIs
vi.mock('@/api/workspace', () => ({
  getFiles: vi.fn(async () => [{ name: 'index.html', path: 'index.html', isDir: false }]),
  getFile: vi.fn(async () => 'mock content'),
  writeFile: vi.fn(async () => {}),
  getGitLog: vi.fn(async () => [{ hash: '123', message: 'Initial commit' }]),
  getGitStatus: vi.fn(async () => 'clean')
}));

describe('Store Module Tests', () => {
  beforeEach(() => {
    // Reset Zustand stores before each test
    useChatStore.setState({ sessionId: null, messages: [], connectionStatus: 'disconnected' });
    useDiffStore.setState({ pendingDiffs: [] });
    useFileStore.setState({ files: [], activeFilePath: null, activeFileContent: '', isLoading: false });
    useGitStore.setState({ commits: [], statusText: '', isLoading: false });
  });

  describe('useChatStore', () => {
    it('initializes with default values', () => {
      const state = useChatStore.getState();
      expect(state.sessionId).toBeNull();
      expect(state.messages).toEqual([]);
      expect(state.connectionStatus).toBe('disconnected');
    });

    it('sets session ID and connection status', () => {
      useChatStore.getState().setSessionId('test-123');
      useChatStore.getState().setConnectionStatus('connected');
      
      const state = useChatStore.getState();
      expect(state.sessionId).toBe('test-123');
      expect(state.connectionStatus).toBe('connected');
    });

    it('adds and streams messages', () => {
      const store = useChatStore.getState();
      store.addMessage({ id: '1', role: 'user', content: 'hello' });
      store.prepareAssistantMessage();
      
      let state = useChatStore.getState();
      expect(state.messages.length).toBe(2);
      expect(state.messages[1].role).toBe('assistant');
      expect(state.messages[1].isStreaming).toBe(true);
      expect(state.messages[1].content).toBe('');

      store.appendToken('World');
      state = useChatStore.getState();
      expect(state.messages[1].content).toBe('World');

      store.finalizeMessage();
      state = useChatStore.getState();
      expect(state.messages[1].isStreaming).toBe(false);
    });
  });

  describe('useDiffStore', () => {
    it('adds and resolves pending diffs', () => {
      const store = useDiffStore.getState();
      
      store.addPendingDiff({
        path: 'test.html',
        oldContent: 'old',
        newContent: 'new',
        diffText: 'diff',
        status: 'pending'
      });

      let state = useDiffStore.getState();
      expect(state.pendingDiffs.length).toBe(1);

      store.resolveDiff('test.html', 'accepted');
      state = useDiffStore.getState();
      // Resolving a diff should remove it from the pending list
      expect(state.pendingDiffs.length).toBe(0);
    });
  });

  describe('useFileStore', () => {
    it('initializes with default values', () => {
      const state = useFileStore.getState();
      expect(state.files).toEqual([]);
      expect(state.activeFilePath).toBeNull();
      expect(state.activeFileContent).toBe('');
      expect(state.isLoading).toBe(false);
    });

    it('sets active content', () => {
      useFileStore.getState().setActiveContent('new content');
      expect(useFileStore.getState().activeFileContent).toBe('new content');
    });

    it('refreshFiles fetches files', async () => {
      await useFileStore.getState().refreshFiles('session-123');
      const state = useFileStore.getState();
      expect(state.files.length).toBe(1);
      expect(state.files[0].name).toBe('index.html');
    });

    it('openFile fetches file content', async () => {
      await useFileStore.getState().openFile('session-123', 'index.html');
      const state = useFileStore.getState();
      expect(state.activeFilePath).toBe('index.html');
      expect(state.activeFileContent).toBe('mock content');
    });
  });

  describe('useGitStore', () => {
    it('initializes with default values', () => {
      const state = useGitStore.getState();
      expect(state.commits).toEqual([]);
      expect(state.statusText).toBe('');
      expect(state.isLoading).toBe(false);
    });

    it('refreshGit fetches log and status', async () => {
      await useGitStore.getState().refreshGit('session-123');
      const state = useGitStore.getState();
      expect(state.commits.length).toBe(1);
      expect(state.commits[0].hash).toBe('123');
      expect(state.statusText).toBe('clean');
    });
  });
});
