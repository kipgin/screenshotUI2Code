import { create } from 'zustand';
import { GitCommit } from '@/types';
import { getGitLog, getGitStatus } from '@/api/workspace';

interface GitState {
  commits: GitCommit[];
  statusText: string;
  isLoading: boolean;
  activeCommitHash: string | null;
  
  refreshGit: (sessionId: string) => Promise<void>;
  checkoutCommit: (sessionId: string, commitHash: string) => Promise<void>;
}

export const useGitStore = create<GitState>((set, get) => ({
  commits: [],
  statusText: '',
  isLoading: false,
  activeCommitHash: null,

  refreshGit: async (sessionId: string) => {
    set({ isLoading: true });
    try {
      const [commits, statusText] = await Promise.all([
        getGitLog(sessionId),
        getGitStatus(sessionId)
      ]);
      set({ commits, statusText, isLoading: false });
    } catch (err) {
      console.error(err);
      set({ isLoading: false });
    }
  },

  checkoutCommit: async (sessionId: string, commitHash: string) => {
    set({ isLoading: true });
    try {
      const { checkoutGitCommit } = await import('@/api/workspace');
      await checkoutGitCommit(sessionId, commitHash);
      set({ activeCommitHash: commitHash });
      
      // Refresh Git logs
      await get().refreshGit(sessionId);
      
      // Refresh Files to reflect checkout state
      const { useFileStore } = await import('./useFileStore');
      const fileStore = useFileStore.getState();
      await fileStore.refreshFiles(sessionId);
      
      // Reload currently open file if active
      if (fileStore.activeFilePath) {
        try {
          await fileStore.openFile(sessionId, fileStore.activeFilePath);
        } catch (e) {
          // File does not exist in this older commit, clear active selection
          useFileStore.setState({ activeFilePath: null, activeFileContent: '' });
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      set({ isLoading: false });
    }
  }
}));
