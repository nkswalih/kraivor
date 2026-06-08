import { create } from 'zustand';
import type { ChatMessage, ChatRoom } from '@/types/api';

interface TypingUser { user_id: string; user_name: string; }

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
}

export const useChatStore = create<ChatState>((set, get) => ({
  rooms: [],
  setRooms: (rooms) => set({ rooms }),
  messagesByRoom: {},
  addMessage: (roomId, msg) => {
    const existing = get().messagesByRoom[roomId] ?? [];
    if (existing.some(m => m.message_id === msg.message_id)) return;
    set({ messagesByRoom: { ...get().messagesByRoom, [roomId]: [...existing, msg] } });
  },
  prependMessages: (roomId, msgs) => {
    const existing = get().messagesByRoom[roomId] ?? [];
    const merged = [...msgs.filter(m => !existing.some(e => e.message_id === m.message_id)), ...existing];
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
      ? current.some(u => u.user_id === user.user_id) ? current : [...current, user]
      : current.filter(u => u.user_id !== user.user_id);
    set({ typingByRoom: { ...get().typingByRoom, [roomId]: next } });
  },
  nextKeyByRoom: {},
  setNextKey: (roomId, key) =>
    set({ nextKeyByRoom: { ...get().nextKeyByRoom, [roomId]: key } }),
}));
