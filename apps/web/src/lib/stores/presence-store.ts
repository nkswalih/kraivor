import { create } from 'zustand';

interface PresenceState {
  /** User ids with a live session somewhere in the dashboard. */
  onlineUserIds: string[];
  /** Full roster snapshot sent by the server right after the handshake. */
  applySync: (userIds: string[]) => void;
  /** A single transition from a connected presence socket. */
  applyPresence: (userId: string, status: 'online' | 'offline') => void;
  /** Test hook: seed state without opening a socket. */
  setOnlineUserIds: (userIds: string[]) => void;
}

export const usePresenceStore = create<PresenceState>(set => ({
  onlineUserIds: [],
  applySync: userIds => set({ onlineUserIds: userIds }),
  applyPresence: (userId, status) =>
    set(state => {
      const current = new Set(state.onlineUserIds);
      if (status === 'online') current.add(userId);
      else current.delete(userId);
      return { onlineUserIds: [...current] };
    }),
  setOnlineUserIds: userIds => set({ onlineUserIds: userIds }),
}));
