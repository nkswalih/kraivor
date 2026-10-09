import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import { InboxDialog } from './inbox-dialog';
import { useInboxDialogStore } from '@/lib/stores/inbox-dialog-store';

/**
 * What the panel itself is responsible for, as opposed to what the sections
 * do inside it.
 *
 * The sections have their own tests. These are about the rules that only hold
 * at the panel level, and both of the interesting ones are about the URL:
 *
 *  - a route change closes the panel, so a link inside a section does not
 *    leave the panel floating over the page it landed on;
 *  - *except* when that route is the inbox route itself, which is a pasted
 *    `/{workspace}/inbox` and whose gate owns the state -- closing there would
 *    strand the user on an empty page.
 *
 * The registry, the rail's queries and Next's dynamic-import machinery are all
 * stubbed, so what is left is the dialog's own logic. The rail itself is real
 * apart from its three hooks, because "the tabs switch sections" is exactly
 * the wiring worth exercising.
 */

const h = vi.hoisted(() => ({
  pathname: '/acme/inbox',
}));

vi.mock('next/navigation', () => ({
  usePathname: () => h.pathname,
  useParams: () => ({ workspace: 'acme' }),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
}));

vi.mock('./inbox-sections', () => ({
  INBOX_SECTIONS: [
    { id: 'all', label: 'All', icon: () => null },
    { id: 'channels', label: 'Channels', icon: () => null },
  ],
  findInboxSection: (id: string) => ({
    id,
    label: id,
    icon: () => null,
    View: () => <div data-testid="section-body">section {id}</div>,
  }),
  prefetchInboxSections: vi.fn(),
}));

/* Four network reads the rail makes purely to draw its badges; the badge
   numbers are covered in inbox-sidebar.test.tsx. */
vi.mock('./use-inbox-data', () => ({
  useUnreadCount: () => ({ data: { unread_count: 0 } }),
  useNotifications: () => ({ data: [] }),
  usePendingInvites: () => ({ data: [], isLoading: false }),
}));

const renderDialog = () => render(<InboxDialog workspaceSlug="acme" />);
const rail = () => screen.queryByRole('navigation', { name: 'Inbox sections' });

/**
 * Opening is a store write from outside React, so it has to be flushed the
 * same way an event handler would be -- otherwise the assertion below reads
 * the DOM before the panel has rendered.
 */
function openPanel() {
  act(() => {
    useInboxDialogStore.getState().open();
  });
}

describe('InboxDialog', () => {
  beforeEach(() => {
    h.pathname = '/acme/inbox';
    useInboxDialogStore.getState().close();
  });

  afterEach(() => {
    cleanup();
    useInboxDialogStore.getState().close();
  });

  it('renders nothing until something asks for it', () => {
    renderDialog();
    expect(rail()).not.toBeInTheDocument();
  });

  it('opens over whatever page is underneath, without navigating', () => {
    h.pathname = '/acme/chat';
    renderDialog();

    openPanel();

    expect(rail()).toBeInTheDocument();
    expect(screen.getByTestId('section-body')).toHaveTextContent('section all');
    /* Opening writes the store, never the URL. */
    expect(h.pathname).toBe('/acme/chat');
  });

  it('lands on All when no section is named', () => {
    renderDialog();
    openPanel();
    expect(useInboxDialogStore.getState().section).toBe('all');
  });

  it('closes when the route changes, so it cannot float over a new page', () => {
    const { rerender } = renderDialog();
    openPanel();
    expect(rail()).toBeInTheDocument();

    h.pathname = '/acme/projects';
    rerender(<InboxDialog workspaceSlug="acme" />);

    expect(useInboxDialogStore.getState().section).toBeNull();
    expect(rail()).not.toBeInTheDocument();
  });

  it('stays open when the inbox route itself is what is showing', () => {
    h.pathname = '/acme/inbox';
    const { rerender } = renderDialog();
    openPanel();

    rerender(<InboxDialog workspaceSlug="acme" />);

    expect(useInboxDialogStore.getState().section).toBe('all');
    expect(rail()).toBeInTheDocument();
  });

  it('switches sections by writing the store, not by navigating', () => {
    h.pathname = '/acme/chat';
    renderDialog();
    openPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Channels' }));

    expect(useInboxDialogStore.getState().section).toBe('channels');
    expect(screen.getByTestId('section-body')).toHaveTextContent('section channels');
    expect(h.pathname).toBe('/acme/chat');
  });
});
