import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import InboxPage from './page';
import { useAuthStore } from '@/lib/stores/auth-store';
import { chatEndpoints } from '@/lib/api/endpoints';

/**
 * Pins both halves of the inbox half of 4.5.
 *
 * The `[workspace]` segment of the URL is a slug; `useAuthStore.workspaceId` is
 * a UUID. Both panels here were building `href={`/${workspaceId}/chat/...}``,
 * and `/${uuid}/chat/${room}` matches no route -- so every DM row and every
 * "Open channel" link in the inbox took the user to a 404, while the identical
 * link in the channel sidebar (which reads the slug) worked.
 *
 * The second test exists because the obvious "fix" is to use the slug
 * everywhere. It must not be: `listRooms` is an API call and takes the UUID.
 * The two identifiers are right in different places, and only these two tests
 * together pin that split.
 */

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspace: 'acme' }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

vi.mock('@/lib/api/endpoints', () => {
  const ROOMS = [
    { id: 'room-dm', name: 'Jane Doe', room_type: 'dm' },
    { id: 'room-ch', name: 'general', room_type: 'channel', topic: 'Everything' },
  ];
  return {
    notificationEndpoints: {
      unreadCount: vi.fn(async () => ({ unread_count: 0 })),
      list: vi.fn(async () => []),
      markRead: vi.fn(async () => ({})),
      dismiss: vi.fn(async () => ({})),
    },
    workspaceEndpoints: {
      myPendingInvitations: vi.fn(async () => []),
      listInvitations: vi.fn(async () => []),
      acceptInvitation: vi.fn(async () => ({})),
      list: vi.fn(async () => ({ results: [] })),
    },
    chatEndpoints: {
      listRooms: vi.fn(async () => ROOMS),
      // Non-empty on purpose: `ChannelsPanel` only renders its "Open channel"
      // link in the branch that maps messages, so an empty channel offers no
      // link at all. That gating is pre-existing and out of scope here -- the
      // defect being pinned is the href, not when the href is shown.
      listMessages: vi.fn(async () => [
        {
          message_id: 'msg-1',
          id: 'msg-1',
          sender_name: 'Jane Doe',
          created_at: '2026-01-01T00:00:00Z',
          content: 'Hello there',
        },
      ]),
    },
  };
});

const WORKSPACE_UUID = 'ws-uuid-1234';

function renderInbox() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <InboxPage />
    </QueryClientProvider>
  );
}

describe('Inbox chat links', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: { id: 'user-1', email: 'me@x.dev', name: 'Me' },
      accessToken: 'token',
      workspaceId: WORKSPACE_UUID,
      workspaceSlug: 'acme',
      workspaces: [{ id: WORKSPACE_UUID, slug: 'acme', name: 'Acme' }],
    });
  });

  afterEach(() => {
    cleanup();
    vi.mocked(chatEndpoints.listRooms).mockClear();
    useAuthStore.setState({
      user: null,
      accessToken: null,
      workspaceId: null,
      workspaceSlug: null,
      workspaces: [],
    });
  });

  it('links a direct message to the workspace slug, not the UUID', async () => {
    renderInbox();

    fireEvent.click(screen.getByRole('button', { name: /members/i }));

    // Fails without the fix: the href was `/${workspaceId}/chat/...`, so it
    // read `/ws-uuid-1234/chat/room-dm` and matched no route.
    const link = await screen.findByRole('link', { name: /jane doe/i });
    expect(link).toHaveAttribute('href', '/acme/chat/room-dm');
  });

  it('still fetches rooms with the workspace UUID', async () => {
    renderInbox();

    fireEvent.click(screen.getByRole('button', { name: /members/i }));
    await screen.findByRole('link', { name: /jane doe/i });

    // The slug is for hrefs. `listRooms(workspacePk)` is an API path and needs
    // the UUID -- swapping it too would turn a working request into a 404 on
    // the server instead.
    expect(chatEndpoints.listRooms).toHaveBeenCalledWith(WORKSPACE_UUID);
  });

  it('links "Open channel" to the workspace slug, not the UUID', async () => {
    renderInbox();

    fireEvent.click(screen.getByRole('button', { name: /channels/i }));
    // The panel only renders its "Open channel" affordance once a room is
    // selected, so this needs the extra click.
    fireEvent.click(await screen.findByRole('button', { name: /#general/i }));

    const link = await screen.findByRole('link', { name: /open channel/i });
    expect(link).toHaveAttribute('href', '/acme/chat/room-ch');
  });
});
