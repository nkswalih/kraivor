import { NextResponse, type NextRequest } from 'next/server';
import { ROUTES } from './constants';

const PUBLIC_PATHS = ['/', '/login', '/register', '/forgot-password', '/verify-email', '/pricing', '/features', '/docs', '/api'];

// Protected paths are any workspaces or settings
const PROTECTED_PATH_PREFIXES = ['/dashboard', '/settings', '/mfa/setup'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublicPath = PUBLIC_PATHS.some((path) => {
    if (path === '/') return pathname === '/';
    return pathname.startsWith(path);
  });

  if (isPublicPath) {
    return NextResponse.next();
  }

  // Next.js dynamic routes like /[workspace] might need broader checks, but let's check kraivor_auth cookie
  // If the path is not public, and we want to enforce auth:
  const isAuthenticated = request.cookies.get('kraivor_auth')?.value === 'true';

  // Alternatively, just checking for access_token or kraivor_auth
  const hasToken = request.cookies.get('access_token')?.value || isAuthenticated;

  if (!hasToken) {
    const loginUrl = new URL(ROUTES.LOGIN, request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};