import React from 'react';
import { Sidebar } from '@/components/layout/sidebar2';
import { Topbar } from '@/components/layout/topbar';

export default function WorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { workspace: string };
}) {
  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      {/* Client Component injected into Server Layout */}
      <Sidebar workspaceSlug={params.workspace} />

      <div className="flex-1 flex flex-col min-w-0 border-l border-border bg-[#0a0a0f]">
        <Topbar workspaceSlug={params.workspace} />
        
        <main className="flex-1 overflow-y-auto relative">
          {children}
        </main>
      </div>
    </div>
  );
}