import { create } from 'zustand';
import type {
  User,
  AuthState,
  LoginCredentials,
  RegisterCredentials,
  ForgotPasswordPayload,
  ResetPasswordPayload,
  VerifyEmailPayload,
  OTPSendRequest,
  OTPVerifyRequest,
} from '@/types/auth';

import { authApi } from '@/lib/api';
import { apiClient } from '@/lib/api/client';
import { isTokenExpired } from '@/lib/utils';

interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<{ mfaRequired: boolean }>;

  register: (credentials: RegisterCredentials) => Promise<void>;

  logout: () => Promise<void>;

  checkAuth: () => Promise<void>;

  setUser: (user: User | null) => void;

  setAccessToken: (token: string | null) => void;

  setMfaToken: (token: string | null) => void;

  forgotPassword: (payload: ForgotPasswordPayload) => Promise<void>;

  resetPassword: (payload: ResetPasswordPayload) => Promise<void>;

  verifyEmail: (payload: VerifyEmailPayload) => Promise<void>;

  resendVerification: (email: string) => Promise<{ message: string }>;

  sendOTP: (payload: OTPSendRequest) => Promise<{ message: string }>;

  verifyOTP: (payload: OTPVerifyRequest) => Promise<void>;

  getSessions: () => Promise<
    Array<{
      session_id: string;
      device_name: string;
      device_type: string;
      ip_address: string;
      last_used_at: string;
      created_at: string;
      is_current: boolean;
    }>
  >;

  revokeSession: (sessionId: string) => Promise<void>;

  revokeAllSessions: () => Promise<void>;

  logoutAll: () => Promise<void>;

  getApiKeys: () => Promise<
    Array<{
      id: string;
      name: string;
      prefix: string;
      created_at: string;
      last_used_at?: string;
    }>
  >;

  createApiKey: (name: string) => Promise<{
    id: string;
    name: string;
    key: string;
    created_at: string;
  }>;

  revokeApiKey: (keyId: string) => Promise<void>;
}

interface ExtendedAuthState extends AuthState {
  mfaToken: string | null;
}

type AuthStore = ExtendedAuthState & AuthActions;

export const useAuthStore = create<AuthStore>()((set, get) => ({
  user: null,

  isAuthenticated: false,

  isLoading: true,

  accessToken: null,

  mfaToken: null,

  login: async (credentials: LoginCredentials) => {
    set({ isLoading: true });

    try {
      const response = await authApi.login(credentials);

      const token = response.accessToken || null;

      if (token) {
        apiClient.setAccessToken(token);
      }

      set({
        user: response.user,
        accessToken: token,
        isAuthenticated: true,
        isLoading: false,
      });

      return {
        mfaRequired: false,
      };
    } catch (error: any) {
      set({ isLoading: false });

      if (error?.mfaRequired && error?.mfaToken) {
        set({
          mfaToken: error.mfaToken,
        });

        return {
          mfaRequired: true,
        };
      }

      throw error;
    }
  },

  register: async (credentials: RegisterCredentials) => {
    set({ isLoading: true });

    try {
      const response = await authApi.register(credentials);

      const token = response.accessToken || null;

      if (token) {
        apiClient.setAccessToken(token);
      }

      set({
        user: response.user,
        accessToken: token,
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
        mfaToken: null,
      });
    }
  },

  checkAuth: async () => {
    try {
      const { accessToken } = get();

      /**
       * VALID ACCESS TOKEN
       */

      if (accessToken && !isTokenExpired(accessToken)) {
        apiClient.setAccessToken(accessToken);

        const user = await authApi.getCurrentUser();

        set({
          user,
          isAuthenticated: true,
          isLoading: false,
        });

        return;
      }

      /**
       * REFRESH USING HTTP ONLY COOKIE
       */

      const refreshResponse = await authApi.refreshToken();

      const newAccessToken = refreshResponse.accessToken;

      if (!newAccessToken) {
        throw new Error('No access token returned');
      }

      apiClient.setAccessToken(newAccessToken);

      const user = await authApi.getCurrentUser();

      set({
        user,
        accessToken: newAccessToken,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      apiClient.clearAccessToken();

      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
        mfaToken: null,
      });
    }
  },

  setUser: (user: User | null) => {
    set({
      user,
      isAuthenticated: !!user,
    });
  },

  setAccessToken: (token: string | null) => {
    if (token) {
      apiClient.setAccessToken(token);
    } else {
      apiClient.clearAccessToken();
    }

    set({
      accessToken: token,
      isAuthenticated: !!token,
    });
  },

  setMfaToken: (token: string | null) => {
    set({ mfaToken: token });
  },

  forgotPassword: async (payload: ForgotPasswordPayload) => {
    await authApi.forgotPassword(payload);
  },

  resetPassword: async (payload: ResetPasswordPayload) => {
    await authApi.resetPassword(payload);
  },

  verifyEmail: async (payload: VerifyEmailPayload) => {
    await authApi.verifyEmail(payload);
  },

  resendVerification: async (email: string) => {
    return await authApi.resendVerification(email);
  },

  sendOTP: async (payload: OTPSendRequest) => {
    return await authApi.sendOTP(payload);
  },

  verifyOTP: async (payload: OTPVerifyRequest) => {
    const response = await authApi.verifyOTP(payload);

    const token = response.accessToken || null;

    if (token) {
      apiClient.setAccessToken(token);
    }

    set({
      user: response.user,
      accessToken: token,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  getSessions: async () => {
    return await authApi.getSessions();
  },

  revokeSession: async (sessionId: string) => {
    await authApi.revokeSession(sessionId);
  },

  revokeAllSessions: async () => {
    await authApi.revokeAllSessions();
  },

  logoutAll: async () => {
    await authApi.logoutAll();
  },

  getApiKeys: async () => {
    return await authApi.getApiKeys();
  },

  createApiKey: async (name: string) => {
    return await authApi.createApiKey(name);
  },

  revokeApiKey: async (keyId: string) => {
    await authApi.revokeApiKey(keyId);
  },
}));

export default useAuthStore;
