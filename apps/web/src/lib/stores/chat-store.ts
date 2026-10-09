import { create } from 'zustand';
import type { ChatMessage, ChatRoom } from '@/types/api';

interface TypingUser {
  user_id: string;
  user_name: string;
}

interface PersistedData {
  unreadCounts: Record<string, number>;
  lastReadAt: Record<string, number>; // roomId → timestamp ms
}

const LS_KEY = 'chat_unread_v2';

function loadData(): PersistedData {
  if (typeof window === 'undefined') return { unreadCounts: {}, lastReadAt: {} };
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) ?? '{"unreadCounts":{},"lastReadAt":{}}');
  } catch {
    return { unreadCounts: {}, lastReadAt: {} };
  }
}

function saveData(data: PersistedData) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  } catch {
    /* quota */
  }
}

interface ChatState {
  rooms: ChatRoom[];
  setRooms: (rooms: ChatRoom[]) => void;
  messagesByRoom: Record<string, ChatMessage[]>;
  addMessage: (roomId: string, msg: ChatMessage) => void;
  prependMessages: (roomId: string, msgs: ChatMessage[]) => void;
  removeMessage: (roomId: string, messageId: string) => void;
  updateMessage: (roomId: string, msg: ChatMessage) => void;
  typingByRoom: Record<string, TypingUser[]>;
  setTyping: (roomId: string, user: TypingUser, isTyping: boolean) => void;
  nextKeyByRoom: Record<string, string | null>;
  setNextKey: (roomId: string, key: string | null) => void;
  /* ─── Unread tracking ──────────────────────── */
  unreadCounts: Record<string, number>;
  lastReadAt: Record<string, number>;
  currentRoomId: string | null;
  incrementUnread: (roomId: string) => void;
  clearUnread: (roomId: string) => void;
  setCurrentRoom: (roomId: string | null) => void;
  syncUnreadFromRooms: (rooms: ChatRoom[]) => void;
  totalUnread: () => number;
}

export const useChatStore = create<ChatState>((set, get) => {
  const initial = loadData();

  return {
    rooms: [],
    setRooms: rooms => set({ rooms }),
    messagesByRoom: {},
    addMessage: (roomId, msg) => {
      const existing = get().messagesByRoom[roomId] ?? [];
      if (existing.some(m => m.message_id === msg.message_id)) return;
      set({ messagesByRoom: { ...get().messagesByRoom, [roomId]: [...existing, msg] } });
      if (roomId !== get().currentRoomId) get().incrementUnread(roomId);
    },
    prependMessages: (roomId, msgs) => {
      const existing = get().messagesByRoom[roomId] ?? [];
      const merged = [
        ...msgs.filter(m => !existing.some(e => e.message_id === m.message_id)),
        ...existing,
      ];
      set({ messagesByRoom: { ...get().messagesByRoom, [roomId]: merged } });
    },
    removeMessage: (roomId, messageId) => {
      const msgs = (get().messagesByRoom[roomId] ?? []).filter(m => m.message_id !== messageId);
      set({ messagesByRoom: { ...get().messagesByRoom, [roomId]: msgs } });
    },
    updateMessage: (roomId, msg) => {
      const msgs = (get().messagesByRoom[roomId] ?? []).map(m =>
        m.message_id === msg.message_id ? msg : m
      );
      set({ messagesByRoom: { ...get().messagesByRoom, [roomId]: msgs } });
    },
    typingByRoom: {},
    setTyping: (roomId, user, isTyping) => {
      const current = get().typingByRoom[roomId] ?? [];
      const next = isTyping
        ? current.some(u => u.user_id === user.user_id)
          ? current
          : [...current, user]
        : current.filter(u => u.user_id !== user.user_id);
      set({ typingByRoom: { ...get().typingByRoom, [roomId]: next } });
    },
    nextKeyByRoom: {},
    setNextKey: (roomId, key) => set({ nextKeyByRoom: { ...get().nextKeyByRoom, [roomId]: key } }),
    /* ─── Unread tracking ──────────────────────── */
    unreadCounts: initial.unreadCounts,
    lastReadAt: initial.lastReadAt,
    currentRoomId: null,
    incrementUnread: roomId => {
      const data: PersistedData = {
        unreadCounts: { ...get().unreadCounts },
        lastReadAt: get().lastReadAt,
      };
      data.unreadCounts[roomId] = (data.unreadCounts[roomId] ?? 0) + 1;
      set(data);
      saveData(data);
    },
    clearUnread: roomId => {
      const data: PersistedData = {
        unreadCounts: { ...get().unreadCounts },
        lastReadAt: get().lastReadAt,
      };
      delete data.unreadCounts[roomId];
      data.lastReadAt[roomId] = Date.now();
      set(data);
      saveData(data);
    },
    setCurrentRoom: roomId => {
      const prev = get().currentRoomId;
      if (prev === roomId) return;
      set({ currentRoomId: roomId });
      if (roomId) get().clearUnread(roomId);
    },
    syncUnreadFromRooms: rooms => {
      const data: PersistedData = {
        unreadCounts: { ...get().unreadCounts },
        lastReadAt: get().lastReadAt,
      };
      let changed = false;
      for (const room of rooms) {
        if (room.unread_count !== undefined && room.unread_count >= 0) {
          const current = data.unreadCounts[room.id] ?? 0;
          if (current !== room.unread_count) {
            data.unreadCounts[room.id] = room.unread_count;
            changed = true;
          }
        }
      }
      if (changed) {
        set(data);
        saveData(data);
      }
    },
    totalUnread: () => {
      return Object.values(get().unreadCounts).reduce((a, b) => a + b, 0);
    },
  };
});
