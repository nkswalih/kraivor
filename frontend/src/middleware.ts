import { NextResponse, type NextRequest } from 'next/server';

const PUBLIC_PATHS = [
  '/',
  '/login',
  '/register',
  '/forgot-password',
  '/verify-email',
  '/reset-password',
  '/mfa',
  '/pricing',
  '/features',
  '/docs',
  '/api',
  '/_next',
  '/favicon.ico',
];

const WORKSPACE_ROUTE_REGEX =
  /^\/[^/]+\/(?:dashboard|analysis|ai|notes|projects|settings)(?:\/.*)?$/;

const isPublicPath = (pathname: string): boolean => {
  return PUBLIC_PATHS.some(path => {
    if (path === '/') return pathname === '/';
    return pathname === path || pathname.startsWith(`${path}/`);
  });
};

const isWorkspaceRoute = (pathname: string): boolean => {
  return WORKSPACE_ROUTE_REGEX.test(pathname);
};

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  if (!isWorkspaceRoute(pathname)) {
    return NextResponse.next();
  }

  // Workspace auth is enforced in AuthProvider because the access token is
  // intentionally stored client-side and is not visible to Next middleware.
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
