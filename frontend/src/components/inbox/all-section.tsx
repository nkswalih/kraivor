'use client';

import { NotificationSplitSection } from './notification-split-section';

/** Every notification. */
export function AllSection() {
  return (
    <NotificationSplitSection emptyMessage="No notifications yet" showMarkAllRead />
  );
}
