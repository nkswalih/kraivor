import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { setAuthCookie, clearAuthCookie } from '@/lib/auth.utils';

export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  avatar?: string;
  mfa_enabled: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  mfaToken?: string | null; // Temporary token during MFA flow
  setAuth: (user: User, accessToken: string) => void;
  setTokens: (accessToken: string) => void;
  setMfaToken: (mfaToken: string) => void;
  updateUser: (user: Partial<User>) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      mfaToken: null,

      setAuth: (user, accessToken) => {
        setAuthCookie();
        set({ user, accessToken, isAuthenticated: true, mfaToken: null });
      },

      setTokens: (accessToken) => {
        setAuthCookie();
        set({ accessToken, isAuthenticated: !!accessToken });
      },

      setMfaToken: (mfaToken) => set({ mfaToken }),

      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),

      logout: () => {
        clearAuthCookie();
        set({ user: null, accessToken: null, isAuthenticated: false, mfaToken: null });
      },
    }),
    {
      name: 'kraivor-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        user: state.user,
        accessToken: state.accessToken, // Persist access token to reduce visual flicker on reload
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);
