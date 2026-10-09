'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useSettingsDialogStore } from '@/lib/stores/settings-dialog-store';

/**
 * `/settings` is the address people type; Preferences is what it shows. Say so
 * in the URL -- the panel is open either way, so this is for the address bar,
 * not for the UI.
 */
export default function SettingsIndexPage() {
  const router = useRouter();
  const params = useParams<{ workspace: string }>();
  const workspace = params?.workspace ?? '';
  const open = useSettingsDialogStore(s => s.open);

  useEffect(() => {
    open('preferences');
    if (workspace) router.replace(`/${workspace}/settings/preferences`);
  }, [workspace, router, open]);

  return null;
}
