'use client';

import { useAutoCollapseSidebar } from '@/lib/hooks/use-auto-collapse-sidebar';

interface SidebarAutoCollapseProps {
  workspaceSlug: string;
  children: React.ReactNode;
}

export function SidebarAutoCollapse({ workspaceSlug, children }: SidebarAutoCollapseProps) {
  useAutoCollapseSidebar(workspaceSlug);
  return <>{children}</>;
}
