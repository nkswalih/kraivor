import { create } from 'zustand';

interface ProfileDialogState {
  /** Username whose card is open, or null when nothing is open. */
  username: string | null;
  open: (username: string) => void;
  close: () => void;
}

/**
 * Why this exists.
 *
 * A profile used to be a route. Every "who is this?" click navigated to
 * `/{workspace}/profile/{username}`, which threw away the page you were on,
 * rewrote the topbar breadcrumb to `Profile / <name>`, and turned the workspace
 * sidebar's own-profile button into a navigation. A card is the Discord
 * answer: one store, one dialog mounted once, and each call site decides only
 * *which* username to show. The hrefs stay real -- `ProfileLink` keeps them for
 * copy-link, middle-click, and the tests that pin them -- so a profile page
 * still exists for pasted URLs; it just is no longer how you visit somebody.
 */
export const useProfileDialogStore = create<ProfileDialogState>(set => ({
  username: null,
  open: username => set({ username }),
  close: () => set({ username: null }),
}));
