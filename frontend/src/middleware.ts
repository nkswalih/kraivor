import { NextResponse, type NextRequest } from 'next/server';
import { ROUTES } from './constants';

const PUBLIC_PATHS = ['/', '/login', '/register', '/forgot-password', '/verify-email', '/pricing', '/features', '/docs', '/api'];

const PROTECTED_PATH_PREFIXES = ['/analysis', '/ai', '/notes', '/projects', '/settings'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublicPath = PUBLIC_PATHS.some((path) => {
    if (path === '/') return pathname === '/';
    return pathname.startsWith(path);
  });

  if (isPublicPath) {
    return NextResponse.next();
  }

  const isProtectedPath = PROTECTED_PATH_PREFIXES.some((prefix) => pathname.startsWith(prefix));

  if (isProtectedPath) {
    const accessToken = request.cookies.get('access_token')?.value;

    if (!accessToken) {
      const loginUrl = new URL(ROUTES.LOGIN, request.url);
      loginUrl.searchParams.set('callbackUrl', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};