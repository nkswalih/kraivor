import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { InboxBell } from './inbox-bell';
import { useInboxDialogStore } from '@/lib/stores/inbox-dialog-store';

/**
 * The topbar's inbox entry point, and the whole of what remains of
 * `InboxPopover`.
 *
 * The popover was deleted because it and the panel were two surfaces for one
 * thing: two copies of the unread query, two accept mutations, and a dropdown
 * that could show a different count from the rail a pixel away. The panel
 * supersedes it on every axis, so nothing needed keeping from its list.
 *
 * What *was* easy to lose is asserted here. The popover did three things the
 * panel itself does not do from the topbar: it carried the unread badge, it
 * responded to a click without navigating anywhere, and it named itself
 * honestly for a screen reader. Dropping the component must not drop those.
 */

const feed = vi.hoisted(() => ({ unread: 0 }));

vi.mock('./use-inbox-data', () => ({
  useUnreadCount: () => ({ data: { unread_count: feed.unread } }),
}));

/** The one button this component renders. */
function bell(): HTMLElement {
  const btn = screen.getByRole('button', { name: /inbox/i });
  return btn;
}

/** The count pill's text, or '' when nothing is unread. */
function badge(btn: HTMLElement): string {
  return btn.querySelector('span')?.textContent ?? '';
}

describe('InboxBell', () => {
  beforeEach(() => {
    cleanup();
    feed.unread = 0;
    useInboxDialogStore.setState({ section: null });
  });

  afterEach(() => {
    cleanup();
  });

  it('opens the panel instead of toggling a dropdown', () => {
    render(<InboxBell />);
    expect(useInboxDialogStore.getState().section).toBeNull();

    fireEvent.click(bell());

    // The panel opens on All -- no navigation, no local open state to drift.
    expect(useInboxDialogStore.getState().section).toBe('all');
  });

  it('renders no badge when nothing is unread', () => {
    render(<InboxBell />);
    expect(badge(bell())).toBe('');
    expect(bell()).toHaveAttribute('aria-label', 'Inbox');
  });

  it('counts unread notifications on the badge', () => {
    feed.unread = 7;
    render(<InboxBell />);
    expect(badge(bell())).toBe('7');
  });

  it('caps the badge at nine-plus so the dot never grows', () => {
    feed.unread = 17;
    render(<InboxBell />);
    expect(badge(bell())).toBe('9+');
  });

  it('says the count out loud, not just in colour', () => {
    feed.unread = 3;
    render(<InboxBell />);
    expect(bell()).toHaveAttribute('aria-label', 'Inbox, 3 unread');
  });
});
