import { coreApi } from '../client';
import type { ChatRoom, ChatMessage, CursorPage, CreateRoomPayload, SendMessagePayload } from '@/types/api';

export const chatEndpoints = {
  listRooms: (workspacePk: string) =>
    coreApi.get<ChatRoom[] | { results: ChatRoom[] }>(`/workspaces/${workspacePk}/chat/rooms/`),

  createRoom: (workspacePk: string, payload: CreateRoomPayload) =>
    coreApi.post<ChatRoom>(`/workspaces/${workspacePk}/chat/rooms/`, payload),

  getRoom: (workspacePk: string, roomPk: string) =>
    coreApi.get<ChatRoom>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/`),

  updateRoom: (workspacePk: string, roomPk: string, payload: Partial<Pick<ChatRoom, 'name' | 'topic'>>) =>
    coreApi.patch<ChatRoom>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/`, payload),

  archiveRoom: (workspacePk: string, roomPk: string) =>
    coreApi.delete<{ status: string }>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/`),

  listMessages: (workspacePk: string, roomPk: string, limit = 50, startKey?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (startKey) params.set('start_key', startKey);
    return coreApi.get<CursorPage<ChatMessage>>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/messages/?${params}`);
  },

  sendMessage: (workspacePk: string, roomPk: string, payload: SendMessagePayload) =>
    coreApi.post<ChatMessage>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/messages/`, payload),

  getMessage: (workspacePk: string, roomPk: string, messagePk: string) =>
    coreApi.get<ChatMessage>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/messages/${messagePk}/`),

  editMessage: (workspacePk: string, roomPk: string, messagePk: string, content: string) =>
    coreApi.patch<ChatMessage>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/messages/${messagePk}/`, { content }),

  deleteMessage: (workspacePk: string, roomPk: string, messagePk: string) =>
    coreApi.delete<{ status: string }>(`/workspaces/${workspacePk}/chat/rooms/${roomPk}/messages/${messagePk}/`),

  searchMessages: (workspacePk: string, roomPk: string, query: string) =>
    coreApi.get<{ results: ChatMessage[]; count: number }>(
      `/workspaces/${workspacePk}/chat/rooms/${roomPk}/messages/search/?q=${encodeURIComponent(query)}`
    ),
};
