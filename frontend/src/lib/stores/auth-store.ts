import { create } from 'zustand';
import type { User, AuthState } from '@/types/auth';
import { clearAuthCookie } from '@/lib/auth-utils';
import { workspaceEndpoints } from '@/lib/api/endpoints';

interface AuthActions {
  setAuth: (user: User, accessToken: string) => void;
  clearAuth: () => void;
  setMfaToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  initWorkspace: () => Promise<string | null>;
  setWorkspace: (id: string, slug: string) => void;
  updateWorkspaceInStore: (id: string, updates: Partial<{ name: string; description: string; slug: string }>) => void;
}

interface ExtendedAuthState extends AuthState {
  mfaToken: string | null;
  workspaceSlug: string | null;
  workspaceId: string | null;
  workspaces: any[];
}

type AuthStore = ExtendedAuthState & AuthActions;

export const useAuthStore = create<AuthStore>()((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  accessToken: null,
  mfaToken: null,
  workspaceSlug: null,
  workspaceId: null,
  workspaces: [],

  setAuth: (user: User, accessToken: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('kraivor_access_token', accessToken);
    }
    set({
      user,
      accessToken,
      isAuthenticated: true,
      isLoading: false,
      mfaToken: null,
    });
  },

  clearAuth: () => {
    clearAuthCookie();
    if (typeof window !== 'undefined') {
      localStorage.removeItem('kraivor_access_token');
    }
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      mfaToken: null,
      workspaceSlug: null,
      workspaceId: null,
      workspaces: [],
    });
  },

  initWorkspace: async () => {
    set({ isLoading: true });
    try {
      const page = await workspaceEndpoints.list(20);
      const ws = page.results?.[0];
      if (ws) {
        set({
          workspaceSlug: ws.slug,
          workspaceId: ws.id,
          workspaces: page.results,
          isLoading: false,
        });
        return ws.slug;
      }
      set({ workspaceSlug: null, workspaceId: null, workspaces: [], isLoading: false });
    } catch {
      set({ workspaceSlug: null, workspaceId: null, workspaces: [], isLoading: false });
    }
    return null;
  },

  setWorkspace: (id: string, slug: string) => set({ workspaceId: id, workspaceSlug: slug }),

  updateWorkspaceInStore: (id: string, updates) =>
    set(state => ({
      workspaces: state.workspaces.map(w => (w.id === id ? { ...w, ...updates } : w)),
    })),

  setMfaToken: (token: string | null) => set({ mfaToken: token }),

  setLoading: (loading: boolean) => set({ isLoading: loading }),
}));

export default useAuthStore;
