import { useAuthStore } from '@/lib/stores';
import { authApi } from '@/lib/api';

export function useAuth() {
  const store = useAuthStore();

  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    accessToken: store.accessToken,
    mfaToken: store.mfaToken,
    login: authApi.login.bind(authApi),
    register: authApi.register.bind(authApi),
    logout: authApi.logout.bind(authApi),
    setMfaToken: store.setMfaToken,
    forgotPassword: authApi.forgotPassword.bind(authApi),
    resetPassword: authApi.resetPassword.bind(authApi),
    verifyEmail: authApi.verifyEmail.bind(authApi),
    resendVerification: authApi.resendVerification.bind(authApi),
    sendOTP: authApi.sendOTP.bind(authApi),
    verifyOTP: authApi.verifyOTP.bind(authApi),
    getSessions: authApi.getSessions.bind(authApi),
    revokeSession: authApi.revokeSession.bind(authApi),
    revokeAllSessions: authApi.revokeAllSessions.bind(authApi),
    logoutAll: authApi.logoutAll.bind(authApi),
    getApiKeys: authApi.getApiKeys.bind(authApi),
    createApiKey: authApi.createApiKey.bind(authApi),
    revokeApiKey: authApi.revokeApiKey.bind(authApi),
  };
}
