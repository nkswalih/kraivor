import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExploreContent } from './explore-content';
import { useCommunityStore } from '@/lib/stores/community-store';
import { useAuthStore } from '@/lib/stores/auth-store';

/**
 * Pins the two things 4.4 changed on this surface, and -- added for 4.6 -- the
 * one thing AUDIT case 5 asks for that presence alone does not prove.
 *
 * Before, a People result was `<button onClick={router.push(...)}>`. A button
 * that navigates cannot be opened in a new tab, cannot be middle-clicked, and
 * is announced as a button -- so a screen reader user hears "Jane Doe, button"
 * and has no idea that activating it leaves the page. It is now a link.
 *
 * It also had no way to message anyone, which is one of Task 4's three stated
 * entry points ("from community, and from search"). The action that goes with
 * it must not live *inside* the link.
 *
 * The case 5 test exists because the other assertions only ever *find* the
 * button. A row that rendered "Message Jane Doe" while passing an empty target
 * would satisfy every one of them; only pressing it tells you whose
 * conversation actually opens.
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

const push = vi.fn();
const createDm = vi.fn();

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspace: 'acme' }),
  // `MessageButton` reads the router at render time and navigates on success,
  // so this has to be a stable spy rather than a fresh `vi.fn()` per call.
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn() }),
}));

vi.mock('@/lib/api/endpoints', () => ({
  chatEndpoints: { createDm: (...args: unknown[]) => createDm(...args) },
  workspaceEndpoints: {},
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
    vi.clearAllMocks();
    createDm.mockResolvedValue({ id: 'room-42' });
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

  it('opens a conversation with the person on the row it was pressed on', async () => {
    renderExplore();

    const button = await screen.findByRole('button', { name: /message jane doe/i });
    fireEvent.click(button);

    // AUDIT case 5 asks for "present and works". Every test above stops at
    // presence, and a row rendering the right label against a hardcoded or
    // stale target would pass all of them -- the conversation would open with
    // somebody else in it and nothing would have looked wrong on this screen.
    await waitFor(() => {
      expect(createDm).toHaveBeenCalledWith('ws-1', 'user-2', 'Jane Doe');
    });
    await waitFor(() => {
      expect(push).toHaveBeenCalledWith('/acme/chat/room-42');
    });

    // Pressing it stays on the list: the identity link is the way out of this
    // surface, and swallowing the click would leave the user stranded.
    expect(screen.getByRole('link', { name: /Jane Doe/i })).toBeInTheDocument();
  });
});
