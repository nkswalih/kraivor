import { useAuthStore } from '@/lib/stores';

export function useAuth() {
  const { user, isAuthenticated, isLoading, accessToken, login, register, logout, checkAuth } = useAuthStore();

  return {
    user,
    isAuthenticated,
    isLoading,
    accessToken,
    login,
    register,
    logout,
    checkAuth,
  };
}