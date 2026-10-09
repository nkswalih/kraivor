import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MessageButton, describeDmFailure } from './message-button';
import { ProfileHeader } from './profile-header';
import { ApiException } from '@/lib/api/error-handler';
import { useAuthStore } from '@/lib/stores/auth-store';
import type { Profile } from '@/types/domain/profiles';

/**
 * The Message button disappeared from `ProfileHeader` in a refactor that was not
 * about the Message button. The endpoint stayed routed and `chatEndpoints.createDm`
 * stayed exported; nothing called either. There was no test to notice, because
 * there was no test.
 *
 * These pin the behaviour that had none, including the parts the old
 * implementation got wrong or left out:
 *
 *   - it swallowed every failure into "Failed to start conversation", including
 *     the 403 the service returns when the target is not a reachable member --
 *     a permanent condition, not something to retry;
 *   - it had no pending state, so a double-click fired two POSTs, and two POSTs
 *     for one pair is what triggers the backend's duplicate-room race;
 *   - it never invalidated the room list, so a conversation started from a profile
 *     did not appear in the sidebar;
 *   - it rendered for logged-out visitors, because the guard only checked for a
 *     selected workspace.
 */

const push = vi.fn();
const toastError = vi.fn();
const createDm = vi.fn();

vi.mock('sonner', () => ({
  toast: { error: (...args: unknown[]) => toastError(...args) },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

vi.mock('@/lib/api/endpoints', () => ({
  chatEndpoints: { createDm: (...args: unknown[]) => createDm(...args) },
}));

const ROOM = { id: 'room-7' };

const baseProfile: Profile = {
  id: 'profile-1',
  user_id: 'user-2',
  username: 'jane',
  display_name: 'Jane Doe',
  bio: 'Builds things.',
  avatar_url: '',
  banner_url: '',
  website_url: 'https://jane.dev',
  github_username: 'jane',
  twitter_username: 'jane',
  linkedin_url: '',
  location: 'Berlin',
  is_public: true,
  is_following: false,
  is_owner: false,
  reputation_score: 42,
  followers_count: 10,
  following_count: 5,
  discussion_count: 3,
  comment_count: 7,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
};

function signedIn(overrides: Record<string, unknown> = {}) {
  useAuthStore.setState({
    workspaceId: 'ws-1',
    workspaceSlug: 'acme',
    accessToken: 'token-abc',
    ...overrides,
  });
}

let invalidate: ReturnType<typeof vi.fn>;

function renderButton(props: Partial<Parameters<typeof MessageButton>[0]> = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  invalidate = vi.spyOn(client, 'invalidateQueries') as unknown as ReturnType<
    typeof vi.fn
  >;

  return render(
    <QueryClientProvider client={client}>
      <MessageButton
        targetUserId="user-2"
        targetName="Jane Doe"
        isOwner={false}
        {...props}
      />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  createDm.mockResolvedValue(ROOM);
  signedIn();
});

describe('MessageButton', () => {
  it('opens the conversation it just created', async () => {
    renderButton();

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith('/acme/chat/room-7'));
    expect(createDm).toHaveBeenCalledWith('ws-1', 'user-2', 'Jane Doe');
  });

  it('refreshes the room list so the conversation shows up in the sidebar', async () => {
    renderButton();

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));

    // Every room list in the app is keyed ['rooms', workspaceId]. Missing this is
    // why a DM started from a profile stayed invisible until a reload.
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ['rooms', 'ws-1'] })
    );
  });

  it('says the person is not a workspace member instead of "try again"', async () => {
    // 403 is permanent: the target left, or never was a member. "Failed to start
    // conversation" -- the only message the old implementation had -- instructs a
    // retry that can never succeed.
    createDm.mockRejectedValue(new ApiException('Forbidden', 403, 'FORBIDDEN'));
    renderButton();

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));

    await waitFor(() =>
      expect(toastError).toHaveBeenCalledWith(
        'You can only message people who are members of this workspace.'
      )
    );
    expect(push).not.toHaveBeenCalled();
  });

  it('does not let the UI distinguish the three reasons for a 403', () => {
    // `DMCreateView` returns one body for "no such account", "left the workspace"
    // and "never was a member". A helpful-sounding "that account no longer
    // exists" is the obvious thing to add here later, and it turns the button
    // into a user-enumeration oracle.
    expect(describeDmFailure(403)).not.toMatch(/not found|does not exist|no longer/i);
  });

  it('refuses a second request while the first is in flight', async () => {
    // Two POSTs for one pair is what the backend duplicate-room race needs. The
    // old button had no pending state at all.
    let release: (room: unknown) => void = () => {};
    createDm.mockImplementation(() => new Promise((resolve) => { release = resolve; }));
    renderButton();

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /message jane doe/i })).toBeDisabled()
    );

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));
    expect(createDm).toHaveBeenCalledTimes(1);

    release(ROOM);
    await waitFor(() => expect(push).toHaveBeenCalled());
  });

  it('announces the pending state out loud, not only with a spinner', async () => {
    // `aria-busy` on a button is not reliably announced, and swapping the icon
    // alone leaves the accessible name unchanged. A sighted user sees a spinner;
    // this is the equivalent for someone who cannot.
    let release: (room: unknown) => void = () => {};
    createDm.mockImplementation(() => new Promise((resolve) => { release = resolve; }));
    renderButton();

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent(/opening a conversation with jane doe/i);
    expect(
      screen.getByRole('button', { name: /message jane doe/i })
    ).toHaveAttribute('aria-busy', 'true');

    release(ROOM);
    await waitFor(() => expect(push).toHaveBeenCalled());
  });

  it('never offers to message yourself', () => {
    renderButton({ isOwner: true });
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('does not render for a visitor with no session', () => {
    // The public profile page lives outside the dashboard, so a visitor there has
    // no workspace selected and the old `!is_owner && workspaceId` guard left a
    // button that failed on press.
    signedIn({ workspaceId: null, workspaceSlug: null, accessToken: null });
    renderButton();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('does not render with a stale workspace but no session', () => {
    // localStorage outlives a sign-out in some paths, so a workspace id alone is
    // not proof of an authenticated session.
    signedIn({ workspaceId: 'ws-1', workspaceSlug: 'acme', accessToken: null });
    renderButton();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('does not render for a profile with no user id', () => {
    // A profile the API returned without `user_id` would otherwise POST a request
    // with an empty target.
    renderButton({ targetUserId: '' });
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('explains an expired session rather than reporting a failure', async () => {
    createDm.mockRejectedValue(new ApiException('Unauthorized', 401, 'UNAUTHORIZED'));
    renderButton();

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));

    await waitFor(() =>
      expect(toastError).toHaveBeenCalledWith(
        'Your session has expired. Sign in again to message them.'
      )
    );
  });

  it('stays on the page when the request never reaches the service', async () => {
    // `handleApiError` gives a network failure statusCode 0, which must not be
    // mistaken for a permission problem or a server error.
    createDm.mockRejectedValue(
      new ApiException('Network error', 0, 'NETWORK_ERROR')
    );
    renderButton();

    await userEvent.click(screen.getByRole('button', { name: /message jane doe/i }));

    await waitFor(() =>
      expect(toastError).toHaveBeenCalledWith(
        'Could not start the conversation. Try again.'
      )
    );
    expect(push).not.toHaveBeenCalled();
  });
});

describe('describeDmFailure', () => {
  it('gives a distinct message per handled status', () => {
    const messages = [400, 401, 403, 429].map(describeDmFailure);
    expect(new Set(messages).size).toBe(messages.length);
  });

  it('falls back to one sentence for every status it does not handle', () => {
    // A 500, a network fault (status 0) and an unrecognised status share one
    // message. Deliberate: an unexpected status is not something the user can act
    // on differently, and inventing a sentence per number would be guessing.
    expect(describeDmFailure(500)).toBe(describeDmFailure(0));
    expect(describeDmFailure(502)).toBe(describeDmFailure(undefined));
  });

  it('does not blame the backend for a local network fault', () => {
    expect(describeDmFailure(0)).not.toMatch(/server/i);
  });
});

/**
 * The two tests below are the ones that actually fail without this change. The
 * tests above exercise `MessageButton` directly, which -- if the component were
 * never rendered from anywhere -- would pass forever while the button stayed
 * absent from the only page that has one.
 */
describe('ProfileHeader wiring', () => {
  function renderHeader(profile: Partial<Profile> = {}) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    invalidate = vi.spyOn(client, 'invalidateQueries') as unknown as ReturnType<
      typeof vi.fn
    >;

    return render(
      <QueryClientProvider client={client}>
        <ProfileHeader
          workspaceSlug="acme"
          profile={{ ...baseProfile, ...profile }}
        />
      </QueryClientProvider>
    );
  }

  it('offers a Message button on someone else’s profile', async () => {
    renderHeader();

    const button = await screen.findByRole('button', { name: /message jane doe/i });
    expect(button).toBeInTheDocument();

    await userEvent.click(button);
    await waitFor(() => expect(push).toHaveBeenCalledWith('/acme/chat/room-7'));
  });

  it('does not offer to message yourself', async () => {
    renderHeader({ is_owner: true });

    // Follow is absent too, but Share and Edit are present -- which is what makes
    // this a real check rather than "the header rendered nothing".
    expect(await screen.findByRole('button', { name: /share/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit profile/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^message/i })).not.toBeInTheDocument();
  });
});