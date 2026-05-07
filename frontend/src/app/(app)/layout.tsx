'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useWorkspaceStore } from '@/lib/stores';
import { useUI } from '@/lib/hooks';
import { Sidebar, Header } from '@/components/layout';
import { cn } from '@/lib/utils';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const workspaceSlug = params.workspace as string;
  const { currentWorkspace, fetchWorkspaces } = useWorkspaceStore();
  const { sidebarCollapsed } = useUI();

  useEffect(() => {
    if (!currentWorkspace) {
      fetchWorkspaces();
    }
  }, [currentWorkspace, fetchWorkspaces]);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar workspaceSlug={workspaceSlug} />
      <div className={cn('transition-all duration-200', sidebarCollapsed ? 'pl-16' : 'pl-64')}>
        <Header workspaceName={currentWorkspace?.name} />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}