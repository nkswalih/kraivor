import { create } from 'zustand';

export type InboxSection = 'all' | 'invitations' | 'workspaces' | 'members' | 'channels';

interface InboxDialogState {
  /** Section on screen, or null when the panel is closed. */
  section: InboxSection | null;
  /** Opens the panel; called with nothing, it lands on All. */
  open: (section?: InboxSection) => void;
  setSection: (section: InboxSection) => void;
  close: () => void;
}

/**
 * Why this exists.
 *
 * The inbox used to be a place you went to: the sidebar linked to
 * `/{workspace}/inbox`, which navigated away from whatever you were doing and
 * swapped the whole screen for a page with its own 200px rail. It read as a
 * destination, and every visit paid for a full route transition.
 *
 * It is a panel now -- a Discord-style modal with a nav rail and a scrollable
 * body -- and this store is what opens it, so the app you were on stays
 * mounted behind it and Esc puts you back exactly where you were. Switching
 * tabs writes the store instead of navigating, which is what lets the panel
 * open instantly and warm every section chunk while it is up.
 *
 * Shaped like `settings-dialog-store` and `profile-dialog-store` on purpose:
 * one nullable value, and the calls that change it. `section === null` *is*
 * the closed state, so there is no boolean to keep in step with it.
 *
 * The route `/{workspace}/inbox` still exists for pasted URLs; it renders
 * nothing and just pushes its section into this store. The URL is the address,
 * never the mechanism.
 */
export const useInboxDialogStore = create<InboxDialogState>(set => ({
  section: null,
  open: (section = 'all') => set({ section }),
  setSection: section => set({ section }),
  close: () => set({ section: null }),
}));
