import React from 'react';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';
import { DashboardNotificationSocket } from '@/components/layout/dashboard-notification-socket';
import { PageShell } from '@/components/layout/page-shell';
import { SidebarAutoCollapse } from '@/components/layout/sidebar-auto-collapse';

export default async function WorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ workspace: string }>;
}) {
  const { workspace } = await params;
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      <DashboardNotificationSocket />

      <SidebarAutoCollapse workspaceSlug={workspace}>
        {/* Client Component injected into Server Layout */}
        <Sidebar workspaceSlug={workspace} />
      </SidebarAutoCollapse>

      <div className="flex-1 flex flex-col min-w-0 border-l border-border bg-background">
        <Topbar workspaceSlug={workspace} />

        <main className="relative flex-1 min-h-0 overflow-hidden">
          <PageShell>{children}</PageShell>
        </main>
      </div>
    </div>
  );
}
