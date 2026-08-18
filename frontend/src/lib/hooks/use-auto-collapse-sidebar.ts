'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { useUIStore } from '@/lib/stores/ui-store';

export function useAutoCollapseSidebar(workspaceSlug: string) {
  const pathname = usePathname();
  const wasOnAiRoute = useRef(false);

  const setSidebarCollapsed = useUIStore(s => s.toggleSidebarCollapse);
  const sidebarCollapsed = useUIStore(s => s.sidebarCollapsed);

  useEffect(() => {
    const isAiRoute = pathname.startsWith(`/${workspaceSlug}/ai`);

    // Auto-collapse when entering AI route
    if (isAiRoute && !sidebarCollapsed) {
      setSidebarCollapsed();
      wasOnAiRoute.current = true;
    }
    // Auto-expand when leaving AI route (only if we collapsed it)
    else if (!isAiRoute && wasOnAiRoute.current && sidebarCollapsed) {
      setSidebarCollapsed();
      wasOnAiRoute.current = false;
    }
  }, [pathname, workspaceSlug, sidebarCollapsed, setSidebarCollapsed]);
}
