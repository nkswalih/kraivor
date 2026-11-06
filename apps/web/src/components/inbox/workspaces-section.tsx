'use client';

import { NotificationSplitSection } from './notification-split-section';

/** The `workspace.*` slice of the feed, same list-detail shape as All. */
export function WorkspacesSection() {
  return (
    <NotificationSplitSection
      filter={n => !!n.notification_type?.startsWith('workspace.')}
      emptyMessage="No workspace notifications"
    />
  );
}
