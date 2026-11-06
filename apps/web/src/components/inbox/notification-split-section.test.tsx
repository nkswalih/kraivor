import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AllSection } from './all-section';
import { WorkspacesSection } from './workspaces-section';
import { notificationEndpoints } from '@/lib/api/endpoints';

/**
 * "Mark all read" is the one thing `InboxPopover` could do that the panel
 * could not, so deleting the popover would have deleted it.
 *
 * It is back on the All list, and the pinning here is deliberately two-sided.
 * The action is global, which is only honest from a view that is showing
 * everything: offering it from Workspaces would clear unread state the person
 * is not looking at, and from a section showing zero unread it would be a
 * button that does nothing. So the tests assert the bar is there when it should
 * be *and* that it stays absent where it must.
 */

const feed = vi.hoisted(() => ({ notifications: null as unknown[] | null }));

vi.mock('./use-inbox-data', () => ({
  useNotifications: () => ({ data: feed.notifications, isLoading: false }),
}));

vi.mock('@/lib/api/endpoints', () => ({
  notificationEndpoints: {
    markAllRead: vi.fn(async () => ({})),
    markRead: vi.fn(async () => ({})),
    dismiss: vi.fn(async () => ({})),
  },
  workspaceEndpoints: {
    acceptInvitation: vi.fn(async () => ({})),
  },
}));

const unread = (id: string, type: string) => ({
  id,
  notification_type: type,
  read_at: null,
  title: `${type} happened`,
  body: 'Something happened in your workspace',
  created_at: '2026-01-01T00:00:00Z',
});

const read = (id: string, type: string) => ({ ...unread(id, type), read_at: '2026-01-01T00:00:00Z' });

function renderSection(node: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

/** The bar's button, or null when it is not offered. */
function markAllButton(): HTMLElement | null {
  return screen.queryByRole('button', { name: /mark all read/i });
}

describe('Mark all read', () => {
  beforeEach(() => {
    cleanup();
    vi.mocked(notificationEndpoints.markAllRead).mockClear();
    feed.notifications = [unread('n1', 'workspace.member.joined'), read('n2', 'profile.follow.new')];
  });

  afterEach(() => {
    cleanup();
  });

  it('offers it on All when something is unread', () => {
    renderSection(<AllSection />);
    expect(markAllButton()).toBeInTheDocument();
    expect(screen.getByText('1 unread')).toBeInTheDocument();
  });

  it('posts to the same endpoint the popover posted to', async () => {
    renderSection(<AllSection />);

    fireEvent.click(markAllButton()!);

    await waitFor(() =>
      expect(notificationEndpoints.markAllRead).toHaveBeenCalledTimes(1)
    );
  });

  it('disappears once everything is read', () => {
    feed.notifications = [read('n1', 'workspace.member.joined')];
    renderSection(<AllSection />);
    expect(markAllButton()).toBeNull();
  });

  it('is not offered from a filtered view, because the action is global', () => {
    feed.notifications = [
      unread('n1', 'workspace.member.joined'),
      unread('n2', 'profile.follow.new'),
    ];
    renderSection(<WorkspacesSection />);
    expect(markAllButton()).toBeNull();
  });
});
