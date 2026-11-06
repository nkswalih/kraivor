import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ShareDialog } from './share-dialog';
import { chatEndpoints, workspaceEndpoints } from '@/lib/api/endpoints';
import { ApiException } from '@/lib/api/error-handler';
import { useAuthStore } from '@/lib/stores/auth-store';
import type { ChatMessage, ChatRoom, WorkspaceMember } from '@/types/api';

/**
 * Pins "made real" for the share dialog's DM affordance (4.5).
 *
 * Before, `handleSend` was `toast.success('Link sent to ... via DM')` with no
 * API call behind it, and the search input above it was bound to a `query` that
 * nothing read -- no result was ever rendered, so `selected` could never become
 * non-null and the Send button could not be reached. A user could type a name,
 * watch nothing happen, and leave believing a message had gone out.
 *
 * Every case here therefore fails on the original source: not with an
 * assertion about a missing call, but because the roster and the Send button
 * simply do not exist.
 *
 * Case 4 and 5 exist because sending is two calls. If only the second fails the
 * room has still been created, and one message cannot honestly describe both
 * outcomes.
 */

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspace: 'acme' }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

vi.mock('@/lib/api/endpoints', () => ({
  chatEndpoints: {
    createDm: vi.fn(),
    sendMessage: vi.fn(),
    listRooms: vi.fn(),
  },
  workspaceEndpoints: {
    getMembers: vi.fn(),
  },
}));

const WORKSPACE_UUID = 'ws-uuid-1234';

const ROOM: ChatRoom = {
  id: 'room-9',
  workspace: WORKSPACE_UUID,
  name: 'Jane Doe',
  room_type: 'dm',
  room_type_display: 'Direct Message',
  topic: '',
  is_active: true,
  last_message_at: null,
  last_message_content: '',
  last_message_sender_name: '',
  participant_user_ids: ['user-1', 'user-2'],
  created_by: 'user-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const MEMBERS: WorkspaceMember[] = [
  {
    id: 'm-1',
    user_id: 'user-1',
    role: 'owner',
    status: 'active',
    joined_at: null,
    invited_by_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    user: { id: 'user-1', name: 'Me Myself', email: 'me@x.dev' },
  },
  {
    id: 'm-2',
    user_id: 'user-2',
    role: 'member',
    status: 'active',
    joined_at: null,
    invited_by_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    user: { id: 'user-2', name: 'Jane Doe', email: 'jane@x.dev' },
  },
  {
    id: 'm-3',
    user_id: 'user-3',
    role: 'member',
    status: 'active',
    joined_at: null,
    invited_by_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    user: { id: 'user-3', name: 'Bob Ray', email: 'bob@x.dev' },
  },
  {
    // Offered by the roster but refused by the backend (4.1), so it must not
    // be offered here either.
    id: 'm-4',
    user_id: 'user-4',
    role: 'member',
    status: 'removed',
    joined_at: null,
    invited_by_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    user: { id: 'user-4', name: 'Gone Person', email: 'gone@x.dev' },
  },
];

const DISCUSSION_URL = `${window.location.origin}/acme/community/disc-1`;

function renderShare() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ShareDialog discussionId="disc-1" title="How should we ship this?" />
    </QueryClientProvider>
  );
}

/** Open the dialog and wait for the roster to land. */
async function openShare() {
  renderShare();
  fireEvent.click(screen.getByRole('button', { name: /^share$/i }));
  return screen.findByRole('button', { name: /jane doe/i });
}

async function chooseAndSend(name: RegExp) {
  fireEvent.click(await screen.findByRole('button', { name }));
  fireEvent.click(await screen.findByRole('button', { name: /send link to/i }));
}

describe('ShareDialog team member search', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: { id: 'user-1', email: 'me@x.dev', name: 'Me Myself' },
      accessToken: 'token',
      workspaceId: WORKSPACE_UUID,
      workspaceSlug: 'acme',
      workspaces: [{ id: WORKSPACE_UUID, slug: 'acme', name: 'Acme' }],
    });
    vi.mocked(workspaceEndpoints.getMembers).mockResolvedValue(MEMBERS);
    vi.mocked(chatEndpoints.createDm).mockReset();
    vi.mocked(chatEndpoints.sendMessage).mockReset();
    vi.mocked(toast.success).mockClear();
    vi.mocked(toast.error).mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.mocked(workspaceEndpoints.getMembers).mockReset();
    useAuthStore.setState({
      user: null,
      accessToken: null,
      workspaceId: null,
      workspaceSlug: null,
      workspaces: [],
    });
  });

  it('lists the workspace roster, minus yourself and minus removed members', async () => {
    await openShare();

    // Fails on the original: `query` drove no fetch and no list rendered, so
    // no roster row could ever appear.
    expect(await screen.findByRole('button', { name: /bob ray/i })).toBeInTheDocument();

    // API path takes the UUID even though the copied link takes the slug.
    expect(workspaceEndpoints.getMembers).toHaveBeenCalledWith(WORKSPACE_UUID);

    // You cannot DM yourself (the backend answers 400), and a removed member
    // is not a member (the backend answers 403) -- offering either only
    // produces a failure the user cannot act on.
    expect(screen.queryByRole('button', { name: /me myself/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /gone person/i })).not.toBeInTheDocument();
  });

  it('narrows the roster as you type', async () => {
    await openShare();

    fireEvent.change(screen.getByPlaceholderText(/search team members/i), {
      target: { value: 'jane' },
    });

    expect(await screen.findByRole('button', { name: /jane doe/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /bob ray/i })).not.toBeInTheDocument();
  });

  it('creates the DM and posts the link into it', async () => {
    vi.mocked(chatEndpoints.createDm).mockResolvedValue(ROOM);
    vi.mocked(chatEndpoints.sendMessage).mockResolvedValue({} as ChatMessage);

    await openShare();
    await chooseAndSend(/jane doe/i);

    await waitFor(() => {
      expect(chatEndpoints.createDm).toHaveBeenCalledWith(
        WORKSPACE_UUID,
        'user-2',
        'Jane Doe'
      );
    });

    // The link is the slug URL, not a UUID one: `/${uuid}/community/...`
    // matches no route, which is the same defect 4.5 fixed on the inbox.
    expect(chatEndpoints.sendMessage).toHaveBeenCalledWith(WORKSPACE_UUID, ROOM.id, {
      content: DISCUSSION_URL,
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Link sent to Jane Doe');
    });

    // Success clears the recipient, so the next send cannot silently repeat
    // against the previous person.
    expect(
      screen.queryByRole('button', { name: /send link to jane doe/i })
    ).not.toBeInTheDocument();
  });

  it('explains a 403 from DM creation in terms of membership', async () => {
    vi.mocked(chatEndpoints.createDm).mockRejectedValue(
      new ApiException('Forbidden', 403, 'FORBIDDEN')
    );
    vi.mocked(chatEndpoints.sendMessage).mockResolvedValue({} as ChatMessage);

    await openShare();
    await chooseAndSend(/jane doe/i);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'You can only message people who are members of this workspace.'
      );
    });
    expect(chatEndpoints.sendMessage).not.toHaveBeenCalled();
  });

  it('says the conversation exists when only the send fails', async () => {
    vi.mocked(chatEndpoints.createDm).mockResolvedValue(ROOM);
    vi.mocked(chatEndpoints.sendMessage).mockRejectedValue(
      new ApiException('Server Error', 500, 'SERVER_ERROR')
    );

    await openShare();
    await chooseAndSend(/jane doe/i);

    // The room was created. "Could not start the conversation" would be untrue
    // and "try again" would create nothing new, so this gets its own sentence.
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'The conversation was created, but the link was not sent. Open it and send the link.'
      );
    });
    expect(chatEndpoints.createDm).toHaveBeenCalled();
  });
});
