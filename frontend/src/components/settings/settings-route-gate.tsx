'use client';

import { useEffect } from 'react';
import { useSettingsDialogStore, type SettingsSection } from '@/lib/stores/settings-dialog-store';

/**
 * Deep links into settings.
 *
 * `/{workspace}/settings/members` and its siblings still exist, because a URL
 * somebody pasted should keep working. But settings is not a page any more, so
 * these routes render nothing at all: they push their section into the dialog
 * store and get out of the way, and the panel opens over whatever the app has
 * behind it. The route is the address, never the mechanism.
 */
export function SettingsRouteGate({ section }: { section: SettingsSection }) {
  const open = useSettingsDialogStore(s => s.open);

  useEffect(() => {
    open(section);
  }, [section, open]);

  return null;
}
