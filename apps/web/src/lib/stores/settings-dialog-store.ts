import { create } from 'zustand';

export type SettingsSection =
  | 'preferences'
  | 'profile'
  | 'inbox'
  | 'security'
  | 'ai-providers'
  | 'billing'
  | 'workspace'
  | 'members';

interface SettingsDialogState {
  /** Section on screen, or null when the panel is closed. */
  section: SettingsSection | null;
  /** Opens the panel; called with nothing, it lands on Preferences. */
  open: (section?: SettingsSection) => void;
  setSection: (section: SettingsSection) => void;
  close: () => void;
}

/**
 * Why this exists.
 *
 * Settings used to be a place you went to: the sidebar linked to
 * `/{workspace}/settings`, which navigated away from whatever you were doing
 * and swapped the whole screen for a `fixed inset-0` overlay. It read as a
 * page, not a panel.
 *
 * It is a panel now -- a Discord-style modal with a nav rail and a scrollable
 * body -- and this store is what opens it, so the app you were on stays
 * mounted behind it and Esc puts you back exactly where you were. Switching
 * sections writes the store instead of navigating, which is what lets the
 * panel open instantly and warm every section chunk while it is up.
 *
 * Shaped like `profile-dialog-store` on purpose: one nullable value, and the
 * calls that change it. `section === null` *is* the closed state, so there is
 * no boolean to keep in step with it.
 *
 * The routes (`/{workspace}/settings` and its eight children) still exist for
 * pasted URLs; they render nothing and just push their section into this
 * store. The URL is the address, never the mechanism.
 */
export const useSettingsDialogStore = create<SettingsDialogState>(set => ({
  section: null,
  open: (section = 'preferences') => set({ section }),
  setSection: section => set({ section }),
  close: () => set({ section: null }),
}));
