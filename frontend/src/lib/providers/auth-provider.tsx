'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/stores';
import { authApi } from '@/lib/api';
import { DEFAULT_DASHBOARD_ROUTE, ROUTES } from '@/constants';

interface AuthProviderProps {
  children: ReactNode;
}

const PUBLIC_ROUTES = [
  ROUTES.HOME,
  ROUTES.LOGIN,
  ROUTES.REGISTER,
  ROUTES.FORGOT_PASSWORD,
  ROUTES.VERIFY_EMAIL,
  ROUTES.RESET_PASSWORD,
  '/mfa',
  ROUTES.PRICING,
  ROUTES.FEATURES,
  ROUTES.DOCS,
];

const AUTH_REDIRECT_ROUTES = [ROUTES.LOGIN, ROUTES.REGISTER];
const WORKSPACE_ROUTE_REGEX =
  /^\/[^/]+\/(?:dashboard|analysis|ai|notes|projects|settings)(?:\/.*)?$/;

const isRouteMatch = (pathname: string, route: string): boolean => {
  if (route === ROUTES.HOME) return pathname === ROUTES.HOME;
  return pathname === route || pathname.startsWith(`${route}/`);
};

const isPublicRoute = (pathname: string): boolean =>
  PUBLIC_ROUTES.some(route => isRouteMatch(pathname, route));

const isAuthRedirectRoute = (pathname: string): boolean =>
  AUTH_REDIRECT_ROUTES.some(route => isRouteMatch(pathname, route));

const isWorkspaceRoute = (pathname: string): boolean =>
  WORKSPACE_ROUTE_REGEX.test(pathname);

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuthStore();
  const initialized = useRef(false);
  const routeIsPublic = isPublicRoute(pathname);
  const routeIsAuthRedirect = isAuthRedirectRoute(pathname);
  const routeIsWorkspace = isWorkspaceRoute(pathname);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    authApi.refreshSession();
  }, []);

  useEffect(() => {
    if (isLoading) return;
    if (routeIsAuthRedirect && isAuthenticated) {
      router.replace(DEFAULT_DASHBOARD_ROUTE);
      return;
    }
    if (!routeIsPublic && !isAuthenticated) {
      router.replace(`${ROUTES.LOGIN}?callbackUrl=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthenticated, isLoading, pathname, routeIsAuthRedirect, routeIsPublic, router]);

  if (isLoading) {
    return null;
  }

  return <>{children}</>;
}
