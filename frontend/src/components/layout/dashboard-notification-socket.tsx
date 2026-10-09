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

  /* Browsers only allow audio after a user gesture, and this is the component
     that plays the notification chime. Nothing it renders can cause a gesture,
     so permission is primed on the first click or tap anywhere.

     This used to happen in `InboxPopover`, which the panel superseded. The
     popover was the only thing triggering it, so deleting it would have
     silently disabled the chime; the listener lives here instead, which is
     where the sound is actually needed. */
  useEffect(() => {
    const prime = () => {
      import('@/lib/notification-sound').then(m => m.requestAudioPermission());
    };
    document.addEventListener('click', prime, { once: true });
    document.addEventListener('touchstart', prime, { once: true });
    return () => {
      document.removeEventListener('click', prime);
      document.removeEventListener('touchstart', prime);
    };
  }, []);

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
