// src/lib/api/auth-api.ts
import apiClient from './client';
import { API_ENDPOINTS } from '@/constants';
import type {
  SignInCredentials,
  RegisterCredentials,
  AuthResponse,
  ForgotPasswordPayload,
  ResetPasswordPayload,
  VerifyEmailPayload,
  User,
  IdentifyResponse,
  OTPSendRequest,
  OTPVerifyRequest,
  MfaVerifyRequest,
} from '@/types/auth';
import { handleApiError } from './error-handler';
import { useAuthStore } from '@/lib/stores/auth-store';

// Helper to reliably get/generate a device_id
const getDeviceId = (): string => {
  if (typeof window === 'undefined') return 'server-device';
  let deviceId = localStorage.getItem('kraivor_device_id');
  if (!deviceId) {
    deviceId = `device-${Math.random().toString(36).substring(2, 15)}`;
    localStorage.setItem('kraivor_device_id', deviceId);
  }
  return deviceId;
};

class AuthApi {
  async identify(email: string): Promise<IdentifyResponse> {
    try {
      return await apiClient.post<IdentifyResponse>(API_ENDPOINTS.AUTH.IDENTIFY, { email });
    } catch (error) {
      throw handleApiError(error);
    }
  }

  // Add this inside the AuthApi class
  async initiateOAuth(provider: 'github' | 'google'): Promise<{ authorization_url: string }> {
    try {
      // Adjust this endpoint path if your apiClient base URL is different
      const response = await apiClient.get<{ authorization_url: string }>(
        `/auth/oauth/${provider}/`
      );
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async login(credentials: SignInCredentials): Promise<{ mfaRequired: boolean }> {
    useAuthStore.getState().setLoading(true);
    try {
      // Inject device_id seamlessly into the payload
      const payload = { ...credentials, device_id: getDeviceId() };

      const response = await apiClient.post<
        AuthResponse & { mfa_required?: boolean; mfa_token?: string }
      >(API_ENDPOINTS.AUTH.PASSWORD, payload);

      if (response.mfa_required && response.mfa_token) {
        useAuthStore.getState().setMfaToken(response.mfa_token);
        useAuthStore.getState().setLoading(false);
        return { mfaRequired: true };
      }

      const token = response.access_token || response.accessToken || '';
      if (token && response.user) {
        useAuthStore.getState().setAuth(response.user, token);
      }
      return { mfaRequired: false };
    } catch (error) {
      useAuthStore.getState().setLoading(false);
      if ((error as any).mfaRequired) throw error;
      throw handleApiError(error);
    }
  }

  async sendOTP(payload: OTPSendRequest): Promise<{ message: string }> {
    try {
      return await apiClient.post<{ message: string }>(API_ENDPOINTS.AUTH.OTP_SEND, payload);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async verifyOTP(payload: OTPVerifyRequest): Promise<void> {
    useAuthStore.getState().setLoading(true);
    try {
      // Inject device_id seamlessly
      const finalPayload = { ...payload, device_id: getDeviceId() };
      const response = await apiClient.post<AuthResponse>(
        API_ENDPOINTS.AUTH.OTP_VERIFY,
        finalPayload
      );

      const token = response.access_token || response.accessToken || '';
      if (token && response.user) {
        useAuthStore.getState().setAuth(response.user, token);
      }
    } catch (error) {
      useAuthStore.getState().setLoading(false);
      throw handleApiError(error);
    }
  }

  async register(credentials: RegisterCredentials): Promise<void> {
    useAuthStore.getState().setLoading(true);
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.REGISTER, credentials);
      const token = response.access_token || response.accessToken || '';
      if (token && response.user) {
        useAuthStore.getState().setAuth(response.user, token);
      }
    } catch (error) {
      useAuthStore.getState().setLoading(false);
      throw handleApiError(error);
    }
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.LOGOUT);
    } catch {
    } finally {
      useAuthStore.getState().clearAuth();
    }
  }

  async refreshSession(): Promise<void> {
    try {
      const response = await apiClient.post<{
        access_token?: string;
        accessToken?: string;
        user?: User;
      }>(API_ENDPOINTS.AUTH.REFRESH);
      const token = response.access_token || response.accessToken || '';
      if (!token) throw new Error('No access token returned from refresh');

      // Store token immediately so subsequent API calls (getCurrentUser) include the Bearer header
      useAuthStore.setState({ accessToken: token, isLoading: false });

      if (response.user) {
        useAuthStore.getState().setAuth(response.user, token);
        return;
      }
      const user = await this.getCurrentUser();
      useAuthStore.getState().setAuth(user, token);
    } catch {
      // If refresh fails (e.g. no session cookie), try recovering token from localStorage
      // so OAuth-logged-in users don't get logged out on page refresh
      const storedToken =
        typeof window !== 'undefined' ? localStorage.getItem('kraivor_access_token') : null;
      if (storedToken) {
        try {
          useAuthStore.setState({ accessToken: storedToken, isLoading: false });
          const user = await this.getCurrentUser();
          useAuthStore.getState().setAuth(user, storedToken);
          return;
        } catch {
          // stored token is invalid/expired — fall through to clearAuth
        }
      }
      useAuthStore.getState().clearAuth();
    }
  }

  async refreshToken(): Promise<string> {
    const response = await apiClient.post<{ access_token?: string; accessToken?: string }>(
      API_ENDPOINTS.AUTH.REFRESH
    );
    const token = response.access_token || response.accessToken || '';
    return token;
  }

  async verifyMfa(payload: MfaVerifyRequest): Promise<void> {
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.MFA_VERIFY, payload);
      const token = response.access_token || response.accessToken || '';
      if (token && response.user) {
        useAuthStore.getState().setAuth(response.user, token);
      }
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async forgotPassword(payload: ForgotPasswordPayload): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, payload);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async resetPassword(payload: ResetPasswordPayload): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.RESET_PASSWORD, payload);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async verifyEmail(payload: VerifyEmailPayload): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.VERIFY_EMAIL, payload);
    } catch (error: any) {
      const apiError = handleApiError(error);
      if (error?.response?.data?.error_code) {
        (apiError as any).errorCode = error.response.data.error_code;
      }
      throw apiError;
    }
  }

  async resendVerification(email: string): Promise<{ message: string }> {
    try {
      return await apiClient.post<{ message: string }>(API_ENDPOINTS.AUTH.RESEND_VERIFICATION, {
        email,
      });
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      return await apiClient.get<User>(API_ENDPOINTS.AUTH.ME);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getSessions(): Promise<
    Array<{
      session_id: string;
      device_name: string;
      device_type: string;
      ip_address: string;
      last_used_at: string;
      created_at: string;
      is_current: boolean;
    }>
  > {
    try {
      const response = await apiClient.get<{
        sessions: Array<{
          session_id: string;
          device_name: string;
          device_type: string;
          ip_address: string;
          last_used_at: string;
          created_at: string;
          is_current: boolean;
        }>;
      }>(API_ENDPOINTS.AUTH.SESSIONS);
      return response.sessions;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async revokeSession(sessionId: string): Promise<void> {
    try {
      await apiClient.delete(API_ENDPOINTS.AUTH.SESSION_REVOKE(sessionId));
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async revokeAllSessions(): Promise<void> {
    try {
      await apiClient.delete(API_ENDPOINTS.AUTH.SESSIONS_ALL);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async logoutAll(): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.LOGOUT_ALL);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getApiKeys(): Promise<
    Array<{ id: string; name: string; prefix: string; created_at: string; last_used_at?: string }>
  > {
    type AK = { id: string; name: string; prefix: string; created_at: string; last_used_at?: string };
    try {
      const data = await apiClient.get<unknown>(API_ENDPOINTS.AUTH.API_KEYS);
      if (Array.isArray(data)) return data as AK[];
      if (data && typeof data === 'object') {
        const obj = data as Record<string, unknown>;
        if (Array.isArray(obj.keys)) return obj.keys as AK[];
        if (Array.isArray(obj.results)) return obj.results as AK[];
      }
      return [];
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async createApiKey(
    name: string
  ): Promise<{ id: string; name: string; key: string; created_at: string }> {
    try {
      return await apiClient.post(API_ENDPOINTS.AUTH.API_KEYS, { name });
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async revokeApiKey(keyId: string): Promise<void> {
    try {
      await apiClient.delete(API_ENDPOINTS.AUTH.API_KEY_REVOKE(keyId));
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

export const authApi = new AuthApi();
export default authApi;
