import React from 'react';
import { SettingsLayoutClient } from '@/components/settings/settings-layout-client';

export default async function SettingsLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ workspace: string }>;
}) {
  const { workspace } = await params;
  return <SettingsLayoutClient workspaceSlug={workspace}>{children}</SettingsLayoutClient>;
}
