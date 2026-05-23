import { create } from 'zustand';
import { authApi } from '@/lib/api';
import { apiClient } from '@/lib/api/client';
import type { User, AuthState, RegisterCredentials, SignInCredentials } from '@/types/auth';

export interface AuthActions {
  login: (credentials: SignInCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => Promise<void>;
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

  login: async (credentials: SignInCredentials) => {
        set({ isLoading: true });
        try {
          const response = await authApi.login(credentials);
          apiClient.setAccessToken(response.accessToken);
          set({
            user: response.user,
            accessToken: response.accessToken,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (credentials: RegisterCredentials) => {
        set({ isLoading: true });
        try {
          const response = await authApi.register(credentials);
          apiClient.setAccessToken(response.accessToken);
          set({
            user: response.user,
            accessToken: response.accessToken,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch {
        } finally {
          apiClient.clearAccessToken();
          set({
            user: null,
            accessToken: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      },

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
