'use client';

import React from 'react';
import { SettingsSidebar } from '@/components/settings/settings-sidebar';

export function SettingsLayoutClient({
  children,
  workspaceSlug,
}: {
  children: React.ReactNode;
  workspaceSlug: string;
}) {
  return (
    <div className="fixed inset-0 z-50 flex bg-krait-obsidian animate-fade-up">
      <SettingsSidebar workspaceSlug={workspaceSlug} />
      <div className="flex-1 flex flex-col overflow-y-auto bg-krait-obsidian">
        <div className="max-w-[840px] mx-auto w-full py-8 px-8">
          {children}
        </div>
      </div>
    </div>
  );
}
