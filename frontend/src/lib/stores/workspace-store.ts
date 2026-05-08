import { create } from 'zustand';
import type { Workspace } from '@/types/workspace';
import { workspaceApi } from '@/lib/api';

interface WorkspaceState {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isLoading: boolean;
  error: string | null;
}

interface WorkspaceActions {
  fetchWorkspaces: () => Promise<void>;
  setCurrentWorkspace: (workspace: Workspace | null) => void;
  createWorkspace: (payload: { name: string; slug: string }) => Promise<Workspace>;
  updateWorkspace: (id: string, payload: Partial<Workspace>) => Promise<void>;
  deleteWorkspace: (id: string) => Promise<void>;
}

type WorkspaceStore = WorkspaceState & WorkspaceActions;

export const useWorkspaceStore = create<WorkspaceStore>((set, get) => ({
  workspaces: [],
  currentWorkspace: null,
  isLoading: false,
  error: null,

  fetchWorkspaces: async () => {
    set({ isLoading: true, error: null });
    try {
      const workspaces = await workspaceApi.list();
      set({ workspaces, isLoading: false });

      if (workspaces.length > 0 && !get().currentWorkspace) {
        set({ currentWorkspace: workspaces[0] });
      }
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  setCurrentWorkspace: (workspace: Workspace | null) => {
    set({ currentWorkspace: workspace });
  },

  createWorkspace: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const workspace = await workspaceApi.create(payload);
      set((state) => ({
        workspaces: [...state.workspaces, workspace],
        currentWorkspace: workspace,
        isLoading: false,
      }));
      return workspace;
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
      throw error;
    }
  },

  updateWorkspace: async (id, payload) => {
    set({ isLoading: true, error: null });
    try {
      const workspace = await workspaceApi.update(id, payload);
      set((state) => ({
        workspaces: state.workspaces.map((w) => (w.id === id ? workspace : w)),
        currentWorkspace: state.currentWorkspace?.id === id ? workspace : state.currentWorkspace,
        isLoading: false,
      }));
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
      throw error;
    }
  },

  deleteWorkspace: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await workspaceApi.delete(id);
      set((state) => {
        const workspaces = state.workspaces.filter((w) => w.id !== id);
        return {
          workspaces,
          currentWorkspace: state.currentWorkspace?.id === id ? null : state.currentWorkspace,
          isLoading: false,
        };
      });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
      throw error;
    }
  },
}));

export default useWorkspaceStore;