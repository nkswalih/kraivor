'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/stores';
import { ROUTES } from '@/constants';

export function useProtectedRoute() {
  const router = useRouter();
  const pathname = usePathname();
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const isLoading = useAuthStore(s => s.isLoading);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      setIsReady(true);
    }
  }, [isLoading]);

  const redirect = useCallback(() => {
    const callbackUrl = encodeURIComponent(pathname);
    router.push(`${ROUTES.LOGIN}?callbackUrl=${callbackUrl}`);
  }, [pathname, router]);

  useEffect(() => {
    if (isReady && !isAuthenticated) {
      redirect();
    }
  }, [isReady, isAuthenticated, redirect]);

  return { isReady, isAuthenticated: isReady && isAuthenticated };
}
