import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConnectRepoDialog } from './connect-repo-dialog';

/**
 * The GitHub App install flow drives a popup window that GitHub sends back to
 * `/oauth/success`, which postMessages `github-app-installed` to `window.opener`
 * and closes itself.
 *
 * The bug these tests pin: `window.open` was called *after* awaiting the
 * install-URL request. Once the handler yields, the browser no longer treats the
 * call as part of the user gesture and the popup blocker rejects it. The old
 * fallback was `window.location.href = url`, so the whole application navigated
 * away to GitHub -- while the dialog simultaneously promised "after granting
 * access you'll return here automatically".
 *
 * The fix opens the window synchronously and assigns its `location` later.
 */

const INSTALL_URL = 'https://github.com/apps/kraivor/installations/new?state=abc123';
const CONFIGURE_URL = 'https://github.com/apps/kraivor/installations/42';

// ─── Mocks ───────────────────────────────────────────────────────────────────

const toastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => toastError(...args),
    success: vi.fn(),
  },
}));

const workspaceId = 'ws-1';

vi.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: (selector: (s: { workspaceId: string }) => unknown) =>
    selector({ workspaceId }),
}));

const installApp = vi.fn();
const listGithubRepos = vi.fn();
const listInstallations = vi.fn();

vi.mock('@/lib/api/endpoints/repositories', () => ({
  repositoryEndpoints: {
    list: vi.fn().mockResolvedValue([]),
    connect: vi.fn(),
    disconnect: vi.fn(),
    listGithubRepos: (...a: unknown[]) => listGithubRepos(...a),
    installApp: (...a: unknown[]) => installApp(...a),
    listInstallations: (...a: unknown[]) => listInstallations(...a),
    importInstallation: vi.fn(),
  },
}));

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** A stand-in for the popup window object. */
function makePopup() {
  return {
    closed: false,
    closedSpy: vi.fn(),
    close: vi.fn(),
    focus: vi.fn(),
    location: { href: '' },
  };
}

function renderDialog() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ConnectRepoDialog open onClose={vi.fn()} />
    </QueryClientProvider>
  );
}

/** Reach the "Authorize with GitHub" screen: admin, zero installations, no error. */
async function showSetupScreen() {
  renderDialog();
  return screen.findByRole('button', { name: /authorize with github/i });
}

/**
 * The waiting and blocked messages appear twice on purpose -- once in the panel
 * body and once in the footer status line -- so these need the plural query.
 */
const waitingText = /waiting for gitHub authorization/i;
const blockedText = /pop-up blocked/i;

beforeEach(() => {
  vi.clearAllMocks();
  listInstallations.mockResolvedValue({ installations: [], can_admin: true });
  listGithubRepos.mockResolvedValue([]);
});

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('GitHub App install popup', () => {
  it('opens the popup synchronously, before the install URL request resolves', async () => {
    // The whole point of the fix. If window.open is not called until after the
    // await, the popup blocker wins and this test fails.
    let resolveInstall: (v: unknown) => void = () => {};
    installApp.mockReturnValue(new Promise(r => { resolveInstall = r; }));

    const popup = makePopup();
    vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window);

    const button = await showSetupScreen();
    fireEvent.click(button);

    // Already open, while the request is still in flight. Opened *blank*: the
    // installation URL does not exist yet at this point.
    expect(window.open).toHaveBeenCalledWith('about:blank', 'github-install', expect.any(String));
    // And not navigated, because there was nothing to navigate to.
    expect(popup.location.href).toBe('');

    resolveInstall({ installation_url: INSTALL_URL, configure_url: null });

    await waitFor(() => expect(popup.location.href).toBe(INSTALL_URL));
  });

  it('navigates the already-open popup to the installation URL', async () => {
    installApp.mockResolvedValue({ installation_url: INSTALL_URL, configure_url: null });
    const popup = makePopup();
    vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window);

    fireEvent.click(await showSetupScreen());

    await waitFor(() => expect(popup.location.href).toBe(INSTALL_URL));
    // Opened once, blank. A second open would be a second window.
    expect(window.open).toHaveBeenCalledTimes(1);
  });

  it('shows the waiting state while the popup is open', async () => {
    installApp.mockResolvedValue({ installation_url: INSTALL_URL, configure_url: null });
    vi.spyOn(window, 'open').mockReturnValue(makePopup() as unknown as Window);

    fireEvent.click(await showSetupScreen());

    expect((await screen.findAllByText(waitingText)).length).toBeGreaterThan(0);
  });

  it('offers a link instead of navigating the app away when the popup is blocked', async () => {
    installApp.mockResolvedValue({ installation_url: INSTALL_URL, configure_url: null });
    // Popup blocker: window.open returns null.
    vi.spyOn(window, 'open').mockReturnValue(null);

    fireEvent.click(await showSetupScreen());

    expect((await screen.findAllByText(blockedText)).length).toBeGreaterThan(0);

    const link = screen.getByRole('link', { name: /open github authorization/i });
    expect(link).toHaveAttribute('href', INSTALL_URL);
    // Safe for a user-supplied target, and does not hand the opener over.
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('does not leave the user stuck on the blocked screen', async () => {
    installApp.mockResolvedValue({ installation_url: INSTALL_URL, configure_url: null });
    vi.spyOn(window, 'open').mockReturnValue(null);

    fireEvent.click(await showSetupScreen());
    await screen.findAllByText(blockedText);

    fireEvent.click(screen.getByRole('button', { name: /^back$/i }));

    expect(await screen.findByRole('button', { name: /authorize with github/i })).toBeInTheDocument();
  });

  it('reports a failed install request instead of failing silently', async () => {
    // Previously only console.error, so the button just looked inert.
    installApp.mockRejectedValue({
      response: { data: { detail: 'GitHub is unreachable.', code: 'upstream_error' } },
    });
    const popup = makePopup();
    vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window);

    fireEvent.click(await showSetupScreen());

    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1));
    expect(toastError.mock.calls[0][0]).toContain('GitHub is unreachable.');
    // The blank popup must not be left hanging with nothing in it.
    expect(popup.close).toHaveBeenCalled();
  });

  it('reports an empty install URL rather than opening a blank window forever', async () => {
    installApp.mockResolvedValue({ installation_url: null, configure_url: null });
    const popup = makePopup();
    vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window);

    fireEvent.click(await showSetupScreen());

    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1));
    expect(popup.close).toHaveBeenCalled();
    expect(screen.queryAllByText(waitingText)).toHaveLength(0);
  });

  it('explains a rejected install that arrives over postMessage', async () => {
    installApp.mockResolvedValue({ installation_url: INSTALL_URL, configure_url: null });
    const popup = makePopup();
    vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window);

    fireEvent.click(await showSetupScreen());
    await screen.findAllByText(waitingText);

    window.dispatchEvent(
      new MessageEvent('message', {
        origin: window.location.origin,
        data: {
          type: 'github-app-install-error',
          error: 'You cancelled the installation.',
        },
      })
    );

    // Was console.error only, so a cancelled install closed the popup silently.
    await waitFor(() => expect(toastError).toHaveBeenCalledWith('You cancelled the installation.'));
  });

  it('ignores install messages from another origin', async () => {
    installApp.mockResolvedValue({ installation_url: INSTALL_URL, configure_url: null });
    vi.spyOn(window, 'open').mockReturnValue(makePopup() as unknown as Window);

    fireEvent.click(await showSetupScreen());
    await screen.findAllByText(waitingText);
    toastError.mockClear();

    window.dispatchEvent(
      new MessageEvent('message', {
        origin: 'https://evil.example',
        data: { type: 'github-app-install-error', error: 'spoofed' },
      })
    );

    expect(toastError).not.toHaveBeenCalled();
  });

  it('does not claim to read email addresses it was never told about', async () => {
    await showSetupScreen();

    // These three scopes were hardcoded with green ticks and asserted whatever
    // the GitHub App happened to be configured with.
    expect(screen.queryByText(/read your verified emails/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/account information/i)).not.toBeInTheDocument();
    // GitHub renders the real permission list on the install page.
    expect(
      screen.getByText(/exactly which permissions are requested/i),
    ).toBeInTheDocument();
  });

  it('promises a pop-up window, which is what it now opens', async () => {
    await showSetupScreen();

    // The old copy said "You'll be redirected to GitHub" while the whole app was
    // in fact navigated away.
    expect(screen.getByText(/taken to GitHub in a pop-up window/i)).toBeInTheDocument();
  });

  it('uses the configure URL when reconfiguring an existing installation', async () => {
    listInstallations.mockResolvedValue({
      can_admin: true,
      installations: [
        {
          id: '1',
          installation_id: 42,
          github_account_login: 'acme',
          github_account_type: 'Organization',
          repositories_synced_at: null,
          repos: [],
        },
      ],
    });
    installApp.mockResolvedValue({ installation_url: null, configure_url: CONFIGURE_URL });
    const popup = makePopup();
    vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window);

    renderDialog();
    fireEvent.click(await screen.findByRole('button', { name: /github app permissions/i }));

    await waitFor(() => expect(popup.location.href).toBe(CONFIGURE_URL));
    expect(installApp).toHaveBeenCalledWith(workspaceId, undefined);
  });
});
