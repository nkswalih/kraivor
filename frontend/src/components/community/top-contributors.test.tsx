import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TopContributors } from './top-contributors';
import { useAuthStore } from '@/lib/stores/auth-store';

/**
 * AUDIT case 4: "community member row -- Message action present and works".
 *
 * The standalone `MessageButton` has its own suite, and `UserRow` has its own;
 * neither covers the join between them. What can go wrong here is in the
 * wiring: the row must pass *its own* person's id and name into the button, and
 * the button must be reachable at all -- this row is the one call site that
 * supplies no `is_owner`, so it leans entirely on the button's derived self
 * check to decide whether to render.
 */

const push = vi.fn();
const createDm = vi.fn();

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspace: 'acme' }),
  useRouter: () => ({ push }),
}));

vi.mock('@/lib/api/endpoints', () => ({
  chatEndpoints: { createDm: (...args: unknown[]) => createDm(...args) },
  workspaceEndpoints: {},
}));

const CONTRIBUTOR = {
  user_id: 'user-2',
  username: 'jane',
  display_name: 'Jane Doe',
  avatar_url: '',
  user_avatar_url: '',
  discussion_count: 4,
  reputation_score: 1200,
};

vi.mock('@/lib/hooks/use-profiles', () => ({
  useTopContributors: () => ({ data: { results: [CONTRIBUTOR] }, isLoading: false }),
}));

function renderContributors() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <TopContributors />
    </QueryClientProvider>
  );
}

function signedIn(userId: string | null = 'user-1') {
  useAuthStore.setState({
    workspaceId: 'ws-1',
    workspaceSlug: 'acme',
    accessToken: 'token-abc',
    user: userId === null ? null : { id: userId, email: 'me@x.dev', name: 'Me' },
  });
}

describe('TopContributors Message action', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createDm.mockResolvedValue({ id: 'room-42' });
    signedIn();
  });

  afterEach(() => {
    cleanup();
    useAuthStore.setState({
      user: null,
      accessToken: null,
      workspaceId: null,
      workspaceSlug: null,
    });
  });

  it('DMs the person named on the row, not some other person', async () => {
    renderContributors();

    const button = await screen.findByRole('button', { name: /message jane doe/i });
    fireEvent.click(button);

    // The failure this catches is a hardcoded or stale target: the button
    // exists, the toast says "sent", and the conversation opens with somebody
    // else in it.
    await waitFor(() => {
      expect(createDm).toHaveBeenCalledWith('ws-1', 'user-2', 'Jane Doe');
    });
    await waitFor(() => {
      expect(push).toHaveBeenCalledWith('/acme/chat/room-42');
    });
  });

  it('does not offer to message yourself, though this row has no is_owner', async () => {
    // `TopContributor` carries no `is_owner`, so the only thing that can hide
    // the button is the button comparing the session's id against the row's.
    // Either signal works, and this is the one that has to.
    signedIn('user-2');

    renderContributors();

    await screen.findByText('Jane Doe');
    expect(
      screen.queryByRole('button', { name: /message jane doe/i })
    ).not.toBeInTheDocument();
    // The row itself is still there -- otherwise this would pass by rendering
    // nothing at all.
    expect(screen.getByRole('link', { name: /jane doe/i })).toBeInTheDocument();
  });

  it('does not render for a visitor with no session', async () => {
    useAuthStore.setState({ accessToken: null, user: null });

    renderContributors();

    await screen.findByText('Jane Doe');
    expect(
      screen.queryByRole('button', { name: /message jane doe/i })
    ).not.toBeInTheDocument();
  });
});
