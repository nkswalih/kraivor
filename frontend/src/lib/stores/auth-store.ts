import { create } from 'zustand';
import type { User, AuthState } from '@/types/auth';
import { clearAuthCookie } from '@/lib/auth-utils';
import { workspaceEndpoints } from '@/lib/api/endpoints';

const WORKSPACE_SLUG_KEY = 'kraivor_workspace_slug';

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
      localStorage.removeItem(WORKSPACE_SLUG_KEY);
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
      const savedSlug = typeof window !== 'undefined' ? localStorage.getItem(WORKSPACE_SLUG_KEY) : null;
      const target = savedSlug ? page.results?.find((w: any) => w.slug === savedSlug) : null;
      const ws = target ?? page.results?.[0];
      if (ws) {
        set({
          workspaceSlug: ws.slug,
          workspaceId: ws.id,
          workspaces: page.results,
          isLoading: false,
        });
        if (typeof window !== 'undefined') {
          localStorage.setItem(WORKSPACE_SLUG_KEY, ws.slug);
        }
        return ws.slug;
      }
      set({ workspaceSlug: null, workspaceId: null, workspaces: [], isLoading: false });
    } catch {
      set({ workspaceSlug: null, workspaceId: null, workspaces: [], isLoading: false });
    }
    return null;
  },

  setWorkspace: (id: string, slug: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(WORKSPACE_SLUG_KEY, slug);
    }
    set({ workspaceId: id, workspaceSlug: slug });
  },

  updateWorkspaceInStore: (id: string, updates) =>
    set(state => ({
      workspaces: state.workspaces.map(w => (w.id === id ? { ...w, ...updates } : w)),
    })),

  setMfaToken: (token: string | null) => set({ mfaToken: token }),

  setLoading: (loading: boolean) => set({ isLoading: loading }),
}));

export default useAuthStore;
