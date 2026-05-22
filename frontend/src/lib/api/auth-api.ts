import apiClient from './client';
import { API_ENDPOINTS } from '@/constants';
import type {
  SignInCredentials,
  RegisterCredentials,
  AuthResponse,
  RefreshTokenResponse,
  ForgotPasswordPayload,
  ResetPasswordPayload,
  VerifyEmailPayload,
  User,
  IdentifyResponse,
  OTPSendRequest,
  OTPVerifyRequest,
} from '@/types/auth';
import { handleApiError } from './error-handler';

class AuthApi {
  async identify(email: string): Promise<IdentifyResponse> {
    try {
      const response = await apiClient.post<IdentifyResponse>(API_ENDPOINTS.AUTH.IDENTIFY, {
        email,
      });
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async login(credentials: SignInCredentials): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<
        AuthResponse & { mfa_required?: boolean; mfa_token?: string }
      >(API_ENDPOINTS.AUTH.PASSWORD, credentials);
      if (response.mfa_required && response.mfa_token) {
        const mfaError: any = new Error('MFA required');
        mfaError.mfaRequired = true;
        mfaError.mfaToken = response.mfa_token;
        throw mfaError;
      }
      return {
        ...response,
        accessToken: response.access_token || response.accessToken || '',
      };
    } catch (error) {
      if ((error as any).mfaRequired) throw error;
      throw handleApiError(error);
    }
  }

  async signInWithPassword(credentials: SignInCredentials): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.PASSWORD, credentials);
      return {
        ...response,
        accessToken: response.access_token || response.accessToken || '',
      };
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async sendOTP(payload: OTPSendRequest): Promise<{ message: string }> {
    try {
      const response = await apiClient.post<{ message: string }>(
        API_ENDPOINTS.AUTH.OTP_SEND,
        payload
      );
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async verifyOTP(payload: OTPVerifyRequest): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.OTP_VERIFY, payload);
      return {
        ...response,
        accessToken: response.access_token || response.accessToken || '',
      };
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async register(credentials: RegisterCredentials): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.REGISTER, credentials);
      return {
        ...response,
        accessToken: response.access_token || response.accessToken || '',
      };
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.LOGOUT);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async refreshToken(): Promise<RefreshTokenResponse> {
    try {
      const response = await apiClient.post<RefreshTokenResponse>(API_ENDPOINTS.AUTH.REFRESH);
      return {
        ...response,
        accessToken: response.access_token || response.accessToken || '',
      };
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
      const response = await apiClient.post<{ message: string }>(
        API_ENDPOINTS.AUTH.RESEND_VERIFICATION,
        { email }
      );
      return response;
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
    try {
      const response = await apiClient.get<
        Array<{
          id: string;
          name: string;
          prefix: string;
          created_at: string;
          last_used_at?: string;
        }>
      >(API_ENDPOINTS.AUTH.API_KEYS);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async createApiKey(
    name: string
  ): Promise<{ id: string; name: string; key: string; created_at: string }> {
    try {
      const response = await apiClient.post<{
        id: string;
        name: string;
        key: string;
        created_at: string;
      }>(API_ENDPOINTS.AUTH.API_KEYS, { name });
      return response;
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

  async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<User>(API_ENDPOINTS.AUTH.ME);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

export const authApi = new AuthApi();
export default authApi;
