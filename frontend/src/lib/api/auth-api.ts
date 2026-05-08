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
      const response = await apiClient.post<IdentifyResponse>(API_ENDPOINTS.AUTH.IDENTIFY, { email });
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async signInWithPassword(credentials: SignInCredentials): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.PASSWORD, credentials);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async sendOTP(payload: OTPSendRequest): Promise<{ message: string }> {
    try {
      const response = await apiClient.post<{ message: string }>(API_ENDPOINTS.AUTH.OTP_SEND, payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async verifyOTP(payload: OTPVerifyRequest): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.OTP_VERIFY, payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async register(credentials: RegisterCredentials): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.AUTH.REGISTER, credentials);
      return response;
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
      return response;
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