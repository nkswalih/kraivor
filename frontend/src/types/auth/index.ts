export type UserRole = 'owner' | 'admin' | 'member' | 'viewer';

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  accessToken: string | null;
}

export type SignInMethod = 'password' | 'otp';
export type NextStep = 'choose_method' | 'verify_email' | 'signup' | 'password' | 'otp';

export interface IdentifyResponse {
  next_step: NextStep;
  user_exists: boolean;
  email_verified: boolean;
  methods?: SignInMethod[];
  message?: string;
}

export interface SignInCredentials {
  email: string;
  password: string;
  device_id?: string;
}

export interface OTPSendRequest {
  email: string;
}

export interface OTPVerifyRequest {
  email: string;
  otp_code: string;
  device_id?: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  name: string;
  organizationName?: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface RefreshTokenResponse {
  accessToken: string;
}

export interface ForgotPasswordPayload {
  email: string;
}

export interface ResetPasswordPayload {
  token: string;
  password: string;
}

export interface VerifyEmailPayload {
  token: string;
}