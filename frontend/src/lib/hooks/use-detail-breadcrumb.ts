'use client';

import { useEffect } from 'react';
import { useBreadcrumbStore } from '@/lib/stores/breadcrumb-store';

export function useDetailBreadcrumb(title: string | null | undefined) {
  const setDetailTitle = useBreadcrumbStore(s => s.setDetailTitle);

  useEffect(() => {
    setDetailTitle(title ?? '');
    return () => setDetailTitle('');
  }, [title, setDetailTitle]);
}
