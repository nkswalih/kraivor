'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { usePresenceStore } from '@/lib/stores/presence-store';
import { PresenceSocket } from '@/lib/ws';

/**
 * Keeps the app-level presence socket alive for the whole dashboard session,
 * mirroring DashboardNotificationSocket. Opened once here — not per page —
 * so "online" means "signed in and using the app", which is what the members
 * rail shows. The roster and every transition land in the presence store
 * that MembersPanel (and anything else presence-aware) reads.
 */
export function DashboardPresence() {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const isLoading = useAuthStore(s => s.isLoading);
  const applySync = usePresenceStore(s => s.applySync);
  const applyPresence = usePresenceStore(s => s.applyPresence);

  useEffect(() => {
    if (!isAuthenticated || isLoading) return;

    const socket = new PresenceSocket();
    socket.onSync = applySync;
    socket.onPresence = applyPresence;
    socket.connect();

    return () => {
      socket.disconnect();
    };
  }, [isAuthenticated, isLoading, applySync, applyPresence]);

  return null;
}
