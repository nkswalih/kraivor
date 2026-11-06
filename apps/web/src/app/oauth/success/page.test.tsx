import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import OAuthSuccessPage from './page';

/**
 * The GitHub App install callback redirects the popup to this page. When
 * `window.opener` survived the round trip from GitHub, it posts
 * `github-app-installed` back to the dialog and closes itself.
 *
 * These pin the case where it did *not* survive -- which is the bug: the page
 * used to fall straight through to redirecting into the workspace, leaving the
 * window open forever because nothing else in the app can close it.
 *
 * The self-close has to be gated, though. Chrome silently refuses `close()` on a
 * window the page did not open, and -- worse -- treats a session history of a
 * single document as script-closable, so an unguarded `close()` here would kill
 * a tab the user legitimately walked to from github.com. Hence: close only a
 * window we can prove is ours (`window.name` set by
 * `window.open(..., 'github-install', ...)`, or our own origin as referrer), and
 * leave everyone else to the redirect.
 */

let search = '';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
}));

vi.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ setAuth: vi.fn(), setLoading: vi.fn() }),
  useAuthStoreApi: () => ({ setState: vi.fn(), getState: vi.fn() }),
}));

vi.mock('@/lib/auth-utils', () => ({ setAuthCookie: vi.fn() }));

vi.mock('@/lib/api/endpoints', () => ({
  workspaceEndpoints: { list: vi.fn().mockResolvedValue({ results: [] }) },
}));

describe('OAuth success page — GitHub App popup', () => {
  let closeSpy: ReturnType<typeof vi.spyOn>;

  const setReferrer = (value: string) =>
    Object.defineProperty(document, 'referrer', { configurable: true, value });

  beforeEach(() => {
    search = 'github_app_installed=1&workspace_id=ws-1&installation_id=142951617&account=nkswalih';
    window.name = '';
    setReferrer('');
    closeSpy = vi.spyOn(window, 'close').mockImplementation(() => {});
    // Report the self-close as successful so the page returns before the redirect
    // branch -- jsdom cannot navigate, and what is under test is whether close()
    // was attempted at all.
    Object.defineProperty(window, 'closed', { configurable: true, get: () => true });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    Reflect.deleteProperty(window, 'closed');
    setReferrer('');
    window.name = '';
  });

  it('closes itself when the opener is gone but the window is one of ours', () => {
    window.name = 'github-install';

    render(<OAuthSuccessPage />);

    expect(closeSpy).toHaveBeenCalledTimes(1);
  });

  it('also treats our own referrer as proof the window is ours', () => {
    // The blocked-popup fallback opens with `<a target="_blank">`, which leaves no
    // `window.name` behind -- but it does navigate from this origin.
    setReferrer(`${window.location.origin}/`);

    render(<OAuthSuccessPage />);

    expect(closeSpy).toHaveBeenCalledTimes(1);
  });

  it('never tries to close a tab the user brought here from github.com', () => {
    window.name = '';
    Object.defineProperty(document, 'referrer', {
      configurable: true,
      value: 'https://github.com/apps/kraivor/installations/new',
    });

    render(<OAuthSuccessPage />);

    // An unguarded close() would kill that tab: Chrome treats a single-document
    // session history as script-closable. It must keep the redirect instead.
    expect(closeSpy).not.toHaveBeenCalled();
  });
});
