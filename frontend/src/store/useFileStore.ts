import { create } from 'zustand';
import { FileNode } from '@/types';
import { getFiles, getFile, writeFile, deleteFile } from '@/api/workspace';

interface FileState {
  files: FileNode[];
  activeFilePath: string | null;
  activeFileContent: string;
  isLoading: boolean;
  
  refreshFiles: (sessionId: string) => Promise<void>;
  openFile: (sessionId: string, path: string) => Promise<void>;
  saveFile: (sessionId: string, content: string) => Promise<void>;
  createFile: (sessionId: string, path: string) => Promise<void>;
  createFolder: (sessionId: string, path: string) => Promise<void>;
  removeFile: (sessionId: string, path: string) => Promise<void>;
  setActiveContent: (content: string) => void;
}

export const useFileStore = create<FileState>((set, get) => ({
  files: [],
  activeFilePath: null,
  activeFileContent: '',
  isLoading: false,

  refreshFiles: async (sessionId: string) => {
    set({ isLoading: true });
    try {
      const files = await getFiles(sessionId);
      set({ files, isLoading: false });
    } catch (err) {
      console.error(err);
      set({ isLoading: false });
    }
  },

  openFile: async (sessionId: string, path: string) => {
    set({ isLoading: true });
    try {
      const content = await getFile(sessionId, path);
      set({ activeFilePath: path, activeFileContent: content, isLoading: false });
    } catch (err) {
      console.error(err);
      set({ isLoading: false });
    }
  },

  saveFile: async (sessionId: string, content: string) => {
    const { activeFilePath } = get();
    if (!activeFilePath) return;
    try {
      await writeFile(sessionId, activeFilePath, content);
      set({ activeFileContent: content });
    } catch (err) {
      console.error(err);
    }
  },

  createFile: async (sessionId: string, path: string) => {
    try {
      await writeFile(sessionId, path, '');
      get().refreshFiles(sessionId);
    } catch (err) {
      console.error(err);
    }
  },

  createFolder: async (sessionId: string, path: string) => {
    try {
      const { createFolder: apiCreateFolder } = await import('@/api/workspace');
      await apiCreateFolder(sessionId, path);
      get().refreshFiles(sessionId);
    } catch (err) {
      console.error(err);
    }
  },

  removeFile: async (sessionId: string, path: string) => {
    try {
      await deleteFile(sessionId, path);
      const { activeFilePath } = get();
      if (activeFilePath === path) {
        set({ activeFilePath: null, activeFileContent: '' });
      }
      get().refreshFiles(sessionId);
    } catch (err) {
      console.error(err);
    }
  },

  setActiveContent: (content: string) => {
    set({ activeFileContent: content });
  }
}));
