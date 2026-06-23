import React from 'react';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';

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
      {/* Client Component injected into Server Layout */}
      <Sidebar workspaceSlug={workspace} />

      <div className="flex-1 flex flex-col min-w-0 border-l border-border bg-background">
        <Topbar workspaceSlug={workspace} />

        <main className="flex-1 flex flex-col overflow-y-auto relative min-h-0">{children}</main>
      </div>
    </div>
  );
}
