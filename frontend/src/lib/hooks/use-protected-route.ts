'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/stores';
import { ROUTES } from '@/constants';

export function useProtectedRoute() {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuthStore();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      setIsReady(true);
    }
  }, [isLoading]);

  useEffect(() => {
    if (isReady && !isAuthenticated) {
      const callbackUrl = encodeURIComponent(pathname);
      router.push(`${ROUTES.LOGIN}?callbackUrl=${callbackUrl}`);
    }
  }, [isReady, isAuthenticated, pathname, router]);

  return { isReady, isAuthenticated: isReady && isAuthenticated };
}