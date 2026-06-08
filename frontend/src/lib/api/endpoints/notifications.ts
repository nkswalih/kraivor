import { coreApi } from '../client';
import type { Notification, MarkAllReadResponse, UnreadCountResponse } from '@/types/api';

export const notificationEndpoints = {
  list: () =>
    coreApi.get<Notification[]>('/notifications/'),

  get: (id: string) =>
    coreApi.get<Notification>(`/notifications/${id}/`),

  markRead: (id: string) =>
    coreApi.post<{ status: string }>(`/notifications/${id}/mark_read/`),

  dismiss: (id: string) =>
    coreApi.post<{ status: string }>(`/notifications/${id}/dismiss/`),

  markAllRead: () =>
    coreApi.post<MarkAllReadResponse>('/notifications/mark_all_read/'),

  unreadCount: () =>
    coreApi.get<UnreadCountResponse>('/notifications/unread_count/'),
};
