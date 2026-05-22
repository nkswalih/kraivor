'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/stores';
import { DEFAULT_DASHBOARD_ROUTE, ROUTES } from '@/constants';
import { isTokenExpired } from '@/lib/utils';

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

const isPublicRoute = (pathname: string): boolean => {
  return PUBLIC_ROUTES.some(route => isRouteMatch(pathname, route));
};

const isAuthRedirectRoute = (pathname: string): boolean => {
  return AUTH_REDIRECT_ROUTES.some(route => isRouteMatch(pathname, route));
};

const isWorkspaceRoute = (pathname: string): boolean => {
  return WORKSPACE_ROUTE_REGEX.test(pathname);
};

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, accessToken, checkAuth } = useAuthStore();
  const initialized = useRef(false);
  const authCheckInFlight = useRef(false);
  const routeIsPublic = isPublicRoute(pathname);
  const routeIsAuthRedirect = isAuthRedirectRoute(pathname);
  const routeIsWorkspace = isWorkspaceRoute(pathname);

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      if (!routeIsWorkspace && !routeIsAuthRedirect && !accessToken) {
        useAuthStore.setState({ isLoading: false });
        return;
      }
      authCheckInFlight.current = true;
      checkAuth().finally(() => {
        authCheckInFlight.current = false;
      });
    }
  }, [accessToken, checkAuth, routeIsAuthRedirect, routeIsWorkspace]);

  useEffect(() => {
    if (!initialized.current) return;
    if (!routeIsWorkspace || isAuthenticated || isLoading) return;
    if (authCheckInFlight.current) return;

    authCheckInFlight.current = true;
    checkAuth().finally(() => {
      authCheckInFlight.current = false;
    });
  }, [checkAuth, isAuthenticated, isLoading, routeIsWorkspace]);

  useEffect(() => {
    if (isLoading || !initialized.current) return;
    if (authCheckInFlight.current) return;

    if (routeIsAuthRedirect) {
      if (isAuthenticated) {
        router.replace(DEFAULT_DASHBOARD_ROUTE);
      }
      return;
    }

    if (routeIsPublic) {
      return;
    }

    if (routeIsWorkspace && !isAuthenticated) {
      const loginUrl = `${ROUTES.LOGIN}?callbackUrl=${encodeURIComponent(pathname)}`;
      router.replace(loginUrl);
      return;
    }
  }, [
    isAuthenticated,
    isLoading,
    pathname,
    routeIsAuthRedirect,
    routeIsPublic,
    routeIsWorkspace,
    router,
  ]);

  useEffect(() => {
    if (!routeIsWorkspace) return;
    if (!accessToken || isLoading) return;

    const tokenExpired = isTokenExpired(accessToken);
    if (tokenExpired) {
      checkAuth();
    }
  }, [accessToken, isLoading, checkAuth, routeIsWorkspace]);

  if (isLoading && (!initialized.current || routeIsWorkspace || routeIsAuthRedirect)) {
    return null;
  }

  return <>{children}</>;
}
