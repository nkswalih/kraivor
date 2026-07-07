import { useRef, useMemo } from 'react';
import { useAuthStore } from '@/lib/stores';
import { authApi } from '@/lib/api';

export function useAuth() {
  const user = useAuthStore(s => s.user);
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const isLoading = useAuthStore(s => s.isLoading);
  const accessToken = useAuthStore(s => s.accessToken);
  const mfaToken = useAuthStore(s => s.mfaToken);
  const setMfaToken = useAuthStore(s => s.setMfaToken);

  const authApiRef = useRef(authApi);
  const login = useMemo(() => authApiRef.current.login.bind(authApiRef.current), []);
  const register = useMemo(() => authApiRef.current.register.bind(authApiRef.current), []);
  const logout = useMemo(() => authApiRef.current.logout.bind(authApiRef.current), []);
  const forgotPassword = useMemo(() => authApiRef.current.forgotPassword.bind(authApiRef.current), []);
  const resetPassword = useMemo(() => authApiRef.current.resetPassword.bind(authApiRef.current), []);
  const verifyEmail = useMemo(() => authApiRef.current.verifyEmail.bind(authApiRef.current), []);
  const resendVerification = useMemo(() => authApiRef.current.resendVerification.bind(authApiRef.current), []);
  const sendOTP = useMemo(() => authApiRef.current.sendOTP.bind(authApiRef.current), []);
  const verifyOTP = useMemo(() => authApiRef.current.verifyOTP.bind(authApiRef.current), []);
  const getSessions = useMemo(() => authApiRef.current.getSessions.bind(authApiRef.current), []);
  const revokeSession = useMemo(() => authApiRef.current.revokeSession.bind(authApiRef.current), []);
  const revokeAllSessions = useMemo(() => authApiRef.current.revokeAllSessions.bind(authApiRef.current), []);
  const logoutAll = useMemo(() => authApiRef.current.logoutAll.bind(authApiRef.current), []);
  const getApiKeys = useMemo(() => authApiRef.current.getApiKeys.bind(authApiRef.current), []);
  const createApiKey = useMemo(() => authApiRef.current.createApiKey.bind(authApiRef.current), []);
  const revokeApiKey = useMemo(() => authApiRef.current.revokeApiKey.bind(authApiRef.current), []);

  return {
    user,
    isAuthenticated,
    isLoading,
    accessToken,
    mfaToken,
    login,
    register,
    logout,
    setMfaToken,
    forgotPassword,
    resetPassword,
    verifyEmail,
    resendVerification,
    sendOTP,
    verifyOTP,
    getSessions,
    revokeSession,
    revokeAllSessions,
    logoutAll,
    getApiKeys,
    createApiKey,
    revokeApiKey,
  };
}
