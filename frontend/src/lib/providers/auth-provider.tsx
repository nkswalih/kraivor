'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/stores';
import { ROUTES } from '@/constants';
import { isTokenExpired } from '@/lib/utils';

interface AuthProviderProps {
  children: ReactNode;
}

const PUBLIC_ROUTES = [
  '/login',
  '/register',
  '/forgot-password',
  '/verify-email',
  '/',
  '/pricing',
  '/features',
  '/docs',
];

const PROTECTED_ROUTES = ['/analysis', '/ai', '/notes', '/projects', '/settings'];

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, accessToken, checkAuth } = useAuthStore();
  const initialized = useRef(false);

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      checkAuth();
    }
  }, [checkAuth]);

  useEffect(() => {
    if (isLoading || !initialized.current) return;

    const isPublicRoute = PUBLIC_ROUTES.some((route) => {
      if (route === '/') return pathname === '/';
      return pathname.startsWith(route);
    });

    if (!isAuthenticated && !isPublicRoute) {
      router.push(ROUTES.LOGIN);
      return;
    }

    if (isAuthenticated && (pathname === ROUTES.LOGIN || pathname === ROUTES.REGISTER)) {
      router.push(ROUTES.DASHBOARD);
    }
  }, [isAuthenticated, isLoading, pathname, router]);

  useEffect(() => {
    if (!accessToken || isLoading) return;

    const tokenExpired = isTokenExpired(accessToken);
    if (tokenExpired) {
      checkAuth();
    }
  }, [accessToken, isLoading, checkAuth]);

  if (isLoading && !initialized.current) {
    return null;
  }

  return <>{children}</>;
}