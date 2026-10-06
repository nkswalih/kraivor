import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExploreContent } from './explore-content';
import { useCommunityStore } from '@/lib/stores/community-store';
import { useAuthStore } from '@/lib/stores/auth-store';

/**
 * Pins the two things 4.4 changed on this surface.
 *
 * Before, a People result was `<button onClick={router.push(...)}>`. A button
 * that navigates cannot be opened in a new tab, cannot be middle-clicked, and
 * is announced as a button -- so a screen reader user hears "Jane Doe, button"
 * and has no idea that activating it leaves the page. It is now a link.
 *
 * It also had no way to message anyone, which is one of Task 4's three stated
 * entry points ("from community, and from search"). The action that goes with
 * it must not live *inside* the link.
 */

const PROFILE = {
  user_id: 'user-2',
  username: 'jane',
  display_name: 'Jane Doe',
  avatar_url: '',
  user_avatar_url: '',
  reputation_score: 42,
  is_owner: false,
};

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspace: 'acme' }),
  // `MessageButton` reads the router at render time, so this has to exist even
  // though no test here presses it.
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

vi.mock('@/lib/hooks/use-community', () => ({
  useDiscussions: () => ({ data: { results: [] }, isLoading: false }),
}));

vi.mock('@/lib/hooks/use-profiles', () => ({
  useProfileSearch: () => ({ data: { results: [PROFILE] }, isLoading: false }),
  useAuthorProfiles: () => ({ data: { profileMap: {} } }),
}));

// Pulling the real DiscussionCard in would drag the whole discussion surface
// into this test; there are no discussions in these fixtures anyway.
vi.mock('./discussion-card', () => ({
  DiscussionCard: () => null,
}));

function renderExplore() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ExploreContent />
    </QueryClientProvider>
  );
}

describe('ExploreContent People results', () => {
  beforeEach(() => {
    // Read straight from the store rather than mocked hooks: this component
    // debounces `searchQuery` through a 200ms timer before it will render a
    // result at all, and faking that timer would test the mock instead.
    useCommunityStore.setState({ searchQuery: 'jane' });
    useAuthStore.setState({
      workspaceId: 'ws-1',
      workspaceSlug: 'acme',
      accessToken: 'token',
      user: { id: 'user-1', email: 'me@x.dev', name: 'Me' },
    });
  });

  afterEach(() => {
    cleanup();
    useCommunityStore.setState({ searchQuery: '' });
    useAuthStore.setState({
      workspaceId: null,
      workspaceSlug: null,
      accessToken: null,
      user: null,
    });
  });

  it('renders each person as a link to their profile', async () => {
    renderExplore();

    // Fails without 4.4: the row was a <button>, so no link role exists.
    const link = await screen.findByRole('link', { name: /Jane Doe/i });
    expect(link).toHaveAttribute('href', '/acme/profile/jane');
  });

  it('does not nest the Message action inside the link', async () => {
    renderExplore();

    const link = await screen.findByRole('link', { name: /Jane Doe/i });
    // `<a><button></a>` is invalid HTML and a browser resolves a click on the
    // inner button by following the outer link -- pressing Message would
    // navigate instead of messaging.
    expect(link.querySelector('button')).toBeNull();
    expect(link).not.toContainElement(screen.getByRole('button', { name: /message jane doe/i }));
  });

  it('offers to message the person without leaving the list', async () => {
    renderExplore();

    const button = await screen.findByRole('button', { name: /message jane doe/i });
    // The accessible name still reaches the link's text, so the button is
    // distinguishable from every other Message button on the page.
    expect(button).toHaveAccessibleName('Message Jane Doe');
  });

  it('hides the Message action on your own profile', async () => {
    useAuthStore.setState({ user: { id: 'user-2', email: 'me@x.dev', name: 'Me' } });

    renderExplore();

    await screen.findByRole('link', { name: /Jane Doe/i });
    expect(
      screen.queryByRole('button', { name: /message jane doe/i })
    ).not.toBeInTheDocument();
  });
});
