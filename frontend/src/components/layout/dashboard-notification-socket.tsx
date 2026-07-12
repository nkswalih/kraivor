'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth-store';
import { NotificationSocket } from '@/lib/ws';
import { playNotificationSound } from '@/lib/notification-sound';
import { sendDesktopNotification } from '@/lib/desktop-notification';
import type { WsServerEvent } from '@/types/ws';

export function DashboardNotificationSocket() {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const isLoading = useAuthStore(s => s.isLoading);
  const queryClient = useQueryClient();
  const notifSocket = useRef<NotificationSocket | null>(null);

  const handleNotification = useCallback(
    (event: WsServerEvent & { type: 'notification' }) => {
      playNotificationSound();

      if (event.title) {
        sendDesktopNotification(event.title, {
          body: event.body || undefined,
          tag: event.id,
          onClick: () => {
            if (event.link) {
              window.location.href = event.link;
            }
          },
        });
      }

      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
    [queryClient],
  );

  useEffect(() => {
    if (!isAuthenticated || isLoading) return;

    const socket = new NotificationSocket();
    notifSocket.current = socket;

    socket.onConnected = () => {
      console.debug('[NotificationSocket] connected');
    };

    socket.onNotification = handleNotification;

    socket.onAuthError = code => {
      console.warn('[NotificationSocket] auth error', code);
    };

    socket.connect();

    return () => {
      socket.disconnect();
      notifSocket.current = null;
    };
  }, [isAuthenticated, isLoading, handleNotification]);

  return null;
}
