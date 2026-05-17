import { create } from 'zustand';
import { DiffInfo } from '@/types';
import { useFileStore } from './useFileStore';

interface DiffState {
  pendingDiffs: DiffInfo[];
  addPendingDiff: (diff: DiffInfo) => void;
  resolveDiff: (path: string, status: 'accepted' | 'rejected') => void;
  clearAll: () => void;
}

export const useDiffStore = create<DiffState>((set) => ({
  pendingDiffs: [],

  addPendingDiff: (diff) => set((state) => {
    // If a diff for this path already exists, update it. Otherwise, add.
    const existing = state.pendingDiffs.findIndex(d => d.path === diff.path);
    if (existing >= 0) {
      const updated = [...state.pendingDiffs];
      updated[existing] = diff;
      return { pendingDiffs: updated };
    }
    return { pendingDiffs: [...state.pendingDiffs, diff] };
  }),

  resolveDiff: (path, status) => set((state) => {
    const updated = state.pendingDiffs.map(d => 
      d.path === path ? { ...d, status } : d
    );
    return { pendingDiffs: updated.filter(d => d.status === 'pending') };
  }),

  clearAll: () => set({ pendingDiffs: [] }),
}));
