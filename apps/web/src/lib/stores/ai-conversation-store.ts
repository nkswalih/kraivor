import { create } from 'zustand';

interface AiConversationState {
  activeConversationId: string | null;
  conversationTitle: string;
  isPinned: boolean;
  setActiveConversation: (id: string | null, title: string, pinned: boolean) => void;
  setConversationTitle: (title: string) => void;
  setPinned: (pinned: boolean) => void;
  clear: () => void;
}

export const useAiConversationStore = create<AiConversationState>((set) => ({
  activeConversationId: null,
  conversationTitle: '',
  isPinned: false,
  setActiveConversation: (id, title, pinned) =>
    set({ activeConversationId: id, conversationTitle: title, isPinned: pinned }),
  setConversationTitle: (title) => set({ conversationTitle: title }),
  setPinned: (pinned) => set({ isPinned: pinned }),
  clear: () =>
    set({ activeConversationId: null, conversationTitle: '', isPinned: false }),
}));
