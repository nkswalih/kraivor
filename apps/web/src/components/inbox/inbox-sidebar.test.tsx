import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { InboxSidebar } from './inbox-sidebar';
import { INBOX_SECTIONS } from './inbox-sections';

/**
 * The rail is the panel's navigation and the reason it feels instant, so these
 * pin what it is allowed to do.
 *
 * It reads the shared registry rather than carrying its own list: a second
 * list would drift from what the dialog actually renders, exactly the way the
 * old `TABS` array in `inbox/page.tsx` could. The counts come from the same
 * three queries the sections read, which is what makes them a prefetch -- so
 * the numbers are asserted too, not just the labels.
 *
 * Items are buttons and not links on purpose. Unlike settings, the inbox has
 * one route and no per-section URLs, so an `href` here would point every item
 * at the same address and pretend clicking navigates. That is a decision worth
 * failing on if someone later "fixes" it into links.
 */

vi.mock('./use-inbox-data', () => ({
  useUnreadCount: () => ({ data: { unread_count: 7 } }),
  useNotifications: () => ({
    data: [
      { id: 'n1', notification_type: 'workspace.member.joined', read_at: null },
      { id: 'n2', notification_type: 'member.joined', read_at: null },
      // Read, so it must not count: `workspace.` alone is not enough.
      { id: 'n3', notification_type: 'workspace.thing.updated', read_at: '2026-01-01T00:00:00Z' },
    ],
  }),
  usePendingInvites: () => ({
    data: [{ id: 'i1', workspaceName: 'Acme', role: 'member', token: 'tok' }],
    isLoading: false,
  }),
}));

/**
 * Find a rail item by its visible label.
 *
 * The count badge lives inside the button, so the computed accessible name is
 * "Members2" rather than "Members" -- asserting on `textContent` keeps the
 * tests about the label a person reads instead of about how a name is
 * assembled, and lets the badge be counted separately.
 */
function railItem(label: string): HTMLElement {
  const match = screen
    .getAllByRole('button')
    .find(b => (b.textContent ?? '').trim().startsWith(label));
  if (!match) throw new Error(`No rail item labelled "${label}"`);
  return match;
}

/** The trailing count pill's text, or '' when the section carries no badge. */
function countOf(label: string): string {
  const badge = railItem(label).querySelector('span:last-child');
  const text = badge?.textContent ?? '';
  return /^\d/.test(text) ? text : '';
}

describe('InboxSidebar', () => {
  beforeEach(() => {
    cleanup();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders every section in the registry', () => {
    render(<InboxSidebar active="all" onSelect={() => {}} />);

    for (const section of INBOX_SECTIONS) {
      expect(railItem(section.label)).toBeInTheDocument();
    }
  });

  it('marks the active section, not whatever is behind the panel', () => {
    render(<InboxSidebar active="members" onSelect={() => {}} />);

    expect(railItem('Members')).toHaveAttribute('aria-current', 'page');
    expect(railItem('All')).not.toHaveAttribute('aria-current');
  });

  it('hands the section to the caller instead of navigating', () => {
    const onSelect = vi.fn();
    render(<InboxSidebar active="all" onSelect={onSelect} />);

    fireEvent.click(railItem('Channels'));
    expect(onSelect).toHaveBeenCalledWith('channels');
  });

  it('draws the counts the old page drew in its TABS array', () => {
    render(<InboxSidebar active="all" onSelect={() => {}} />);

    expect(countOf('All')).toBe('7'); // unread_count
    expect(countOf('Invitations')).toBe('1'); // one pending invite
    expect(countOf('Workspaces')).toBe('1'); // workspace.* and unread
    expect(countOf('Members')).toBe('2'); // mentions "member", unread
    expect(countOf('Channels')).toBe(''); // never counted
  });

  it('is buttons, not links -- the inbox has one route and no per-tab URLs', () => {
    render(<InboxSidebar active="all" onSelect={() => {}} />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(railItem('All')).toBeInTheDocument();
  });
});
