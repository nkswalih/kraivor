import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TopContributors } from './top-contributors';
import { useAuthStore } from '@/lib/stores/auth-store';

/**
 * AUDIT case 4 used to require a working Message action on each contributor
 * row -- and this file tested exactly that wiring. The requirement has
 * changed: direct messages start from the member's own profile, so the
 * ranking list must not carry a message button of its own. What stays true
 * is the row's other job: it must link to the profile where that button
 * lives, and it must keep showing the discussion count it ranks on.
 */

const push = vi.fn();

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspace: 'acme' }),
  useRouter: () => ({ push }),
}));

vi.mock('@/lib/api/endpoints', () => ({
  chatEndpoints: { createDm: vi.fn() },
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

describe('TopContributors rows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it('links the row to that member’s profile, where the DM button lives', async () => {
    renderContributors();

    const link = await screen.findByRole('link', { name: /jane doe/i });
    expect(link).toHaveAttribute('href', '/acme/profile/jane');
  });

  it('offers no direct-message action in the list, even when signed in', async () => {
    // The button this suite used to drive was the only message affordance
    // here; now none may appear -- the profile page owns that action.
    renderContributors();

    await screen.findByText('Jane Doe');
    expect(
      screen.queryByRole('button', { name: /message/i })
    ).not.toBeInTheDocument();
  });

  it('keeps showing the discussion count the ranking is based on', async () => {
    renderContributors();

    expect(await screen.findByText('4 discussions')).toBeInTheDocument();
  });
});
