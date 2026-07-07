'use client';

import { Component, useEffect, useRef, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { authApi } from '@/lib/api/auth-api';
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

function AuthSplashGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLoading = useAuthStore(s => s.isLoading);

  if (isLoading && !isPublicRoute(pathname)) {
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

function AuthEffects() {
  const router = useRouter();
  const pathname = usePathname();

  const initialized = useRef(false);
  const sessionReady = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    if (isPublicRoute(pathname) || isAuthRedirectRoute(pathname)) {
      useAuthStore.getState().setLoading(false);
      sessionReady.current = true;
      return;
    }

    const { initWorkspace } = useAuthStore.getState();
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
  }, [pathname]);

  const isLoading = useAuthStore(s => s.isLoading);
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const workspaceSlug = useAuthStore(s => s.workspaceSlug);
  const setLoading = useAuthStore(s => s.setLoading);

  /* ── Forced timeout: never stay stuck on loading beyond 20s ── */
  useEffect(() => {
    if (!isLoading) return;
    const id = setTimeout(() => {
      console.error('[AuthProvider] Loading timeout reached — forcing isLoading=false');
      setLoading(false);
    }, 20_000);
    return () => clearTimeout(id);
  }, [isLoading, setLoading]);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthRedirectRoute(pathname) && isAuthenticated) {
      const redirect = workspaceSlug ? `/${workspaceSlug}` : '/new-workspace';
      router.replace(redirect);
      return;
    }
    if (
      sessionReady.current &&
      !isPublicRoute(pathname) &&
      !isAuthenticated &&
      !pathname.startsWith('/oauth/')
    ) {
      router.replace(`${ROUTES.LOGIN}?callbackUrl=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthenticated, isLoading, pathname, router, workspaceSlug]);

  return null;
}

class AuthErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch() {
    useAuthStore.getState().setLoading(false);
  }

  render() {
    if (this.state.hasError) {
      return (
        <AuthSplashGuard>
          <>{null}</>
        </AuthSplashGuard>
      );
    }
    return this.props.children;
  }
}

export function AuthProvider({ children }: AuthProviderProps) {
  return (
    <AuthErrorBoundary>
      <AuthEffects />
      <AuthSplashGuard>
        {children}
      </AuthSplashGuard>
    </AuthErrorBoundary>
  );
}
