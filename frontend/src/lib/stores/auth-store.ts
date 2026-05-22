import { create } from 'zustand';
import type { User, AuthState } from '@/types/auth';

interface AuthActions {
  setAuth: (user: User, accessToken: string) => void;
  clearAuth: () => void;
  setMfaToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
}

interface ExtendedAuthState extends AuthState {
  mfaToken: string | null;
}

type AuthStore = ExtendedAuthState & AuthActions;

export const useAuthStore = create<AuthStore>()((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  accessToken: null,
  mfaToken: null,

  setAuth: (user: User, accessToken: string) =>
    set({
      user,
      accessToken,
      isAuthenticated: true,
      isLoading: false,
      mfaToken: null,
    }),

  clearAuth: () =>
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      mfaToken: null,
    }),

  setMfaToken: (token: string | null) => set({ mfaToken: token }),

  setLoading: (loading: boolean) => set({ isLoading: loading }),
}));

export default useAuthStore;
