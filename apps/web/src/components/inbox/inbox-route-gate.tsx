'use client';

import { useEffect } from 'react';
import { useInboxDialogStore } from '@/lib/stores/inbox-dialog-store';

/**
 * Deep links into the inbox.
 *
 * `/{workspace}/inbox` still exists, because a URL somebody pasted should keep
 * working. But the inbox is not a page any more, so this route renders nothing
 * at all: it pushes its section into the dialog store and gets out of the way,
 * and the panel opens over whatever the app has behind it. The route is the
 * address, never the mechanism.
 */
export function InboxRouteGate() {
  const open = useInboxDialogStore(s => s.open);

  useEffect(() => {
    open();
  }, [open]);

  return null;
}
