'use client';

import { useMemo } from 'react';
import { usePresenceStore } from '@/lib/stores/presence-store';

/**
 * Live set of online user ids, fed by the dashboard-level presence socket
 * (see DashboardPresence). App-level, not room-level: a member counts as
 * online while they have the dashboard open anywhere — sitting in another
 * channel or browsing the community pages still counts.
 */
export function usePresence(): Set<string> {
  const onlineUserIds = usePresenceStore(s => s.onlineUserIds);
  return useMemo(() => new Set(onlineUserIds), [onlineUserIds]);
}
