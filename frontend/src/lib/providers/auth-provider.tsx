'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth-store';
import { authApi } from '@/lib/api/auth-api';
import { NotificationSocket } from '@/lib/ws';
import { ROUTES } from '@/constants';

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
  '/oauth',
  ROUTES.PRICING,
  ROUTES.FEATURES,
  ROUTES.DOCS,
  '/new-workspace',
];

const AUTH_REDIRECT_ROUTES = [ROUTES.LOGIN, ROUTES.REGISTER];

const isRouteMatch = (pathname: string, route: string): boolean => {
  if (route === ROUTES.HOME) return pathname === ROUTES.HOME;
  return pathname === route || pathname.startsWith(`${route}/`);
};

const isPublicRoute = (pathname: string): boolean =>
  PUBLIC_ROUTES.some(route => isRouteMatch(pathname, route));

const isAuthRedirectRoute = (pathname: string): boolean =>
  AUTH_REDIRECT_ROUTES.some(route => isRouteMatch(pathname, route));

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, workspaceSlug, initWorkspace } = useAuthStore();
  const initialized = useRef(false);
  const sessionReady = useRef(false);
  const routeIsPublic = isPublicRoute(pathname);
  const routeIsAuthRedirect = isAuthRedirectRoute(pathname);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    authApi
      .refreshSession()
      .then(() => {
        initWorkspace().then(() => {
          const pathSegments = pathname.split('/').filter(Boolean);
          const slugFromUrl = pathSegments[0];
          if (slugFromUrl && !isPublicRoute(pathname) && !isAuthRedirectRoute(pathname)) {
            const state = useAuthStore.getState();
            if (state.workspaceSlug !== slugFromUrl && state.workspaces.length > 0) {
              const ws = state.workspaces.find((w: { slug: string }) => w.slug === slugFromUrl);
              if (ws) {
                state.setWorkspace(ws.id, ws.slug);
              }
            }
          }
        });
      })
      .finally(() => {
        sessionReady.current = true;
      });
  }, [initWorkspace, pathname]);

  useEffect(() => {
    if (isLoading) return;
    if (routeIsAuthRedirect && isAuthenticated) {
      const redirect = workspaceSlug ? `/${workspaceSlug}` : '/new-workspace';
      router.replace(redirect);
      return;
    }
    if (
      sessionReady.current &&
      !routeIsPublic &&
      !isAuthenticated &&
      !pathname.startsWith('/oauth/')
    ) {
      router.replace(`${ROUTES.LOGIN}?callbackUrl=${encodeURIComponent(pathname)}`);
    }
  }, [
    isAuthenticated,
    isLoading,
    pathname,
    routeIsAuthRedirect,
    routeIsPublic,
    router,
    workspaceSlug,
  ]);

  /* ─── Real-time notification socket ──────────────────────────── */
  const queryClient = useQueryClient();
  const notifSocket = useRef<NotificationSocket | null>(null);

  useEffect(() => {
    if (!isAuthenticated || isLoading) return;

    const socket = new NotificationSocket();
    notifSocket.current = socket;

    socket.onConnected = () => {
      console.debug('[NotificationSocket] connected');
    };

    socket.onNotification = event => {
      // Invalidate queries so inbox popover and inbox page update in real-time
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    };

    socket.onAuthError = code => {
      console.warn('[NotificationSocket] auth error', code);
    };

    socket.connect();

    return () => {
      socket.disconnect();
      notifSocket.current = null;
    };
  }, [isAuthenticated, isLoading, queryClient]);

  /* ─── Hybrid loading: show a branded splash screen while auth resolves ─── */
  if (isLoading) {
    return (
      <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#0A0A0B]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-venom-yellow/10 flex items-center justify-center">
            <div className="w-5 h-5 border-2 border-venom-yellow border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-[13px] text-text-tertiary animate-pulse">Loading Kraivor...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
