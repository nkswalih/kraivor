import { coreApi } from '../client';
import type { Notification, MarkAllReadResponse, UnreadCountResponse } from '@/types/api';

export const notificationEndpoints = {
  list: async () => {
    const data = await coreApi.get<{ results: Notification[] }>('/notifications/');
    return data.results ?? [];
  },

  get: (id: string) => coreApi.get<Notification>(`/notifications/${id}/`),

  markRead: (id: string) => coreApi.patch<Notification>(`/notifications/${id}/read/`),

  dismiss: (id: string) => coreApi.delete<void>(`/notifications/${id}/`),

  markAllRead: () => coreApi.post<MarkAllReadResponse>('/notifications/'),

  unreadCount: () => coreApi.get<UnreadCountResponse>('/notifications/unread_count/'),
};
