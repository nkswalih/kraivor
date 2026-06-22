'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { setAuthCookie } from '@/lib/auth-utils';
import { config } from '@/config';
import { workspaceEndpoints } from '@/lib/api/endpoints';
import type { User } from '@/types/auth';

type Stage = 'processing' | 'redirecting' | 'error';

export default function OAuthSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore(s => s.setAuth);
  const setLoading = useAuthStore(s => s.setLoading);
  const [stage, setStage] = useState<Stage>('processing');
  const [error, setError] = useState('');
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const accessToken = searchParams.get('access_token');
    const isGitHubAppInstalled = searchParams.get('github_app_installed') === '1';
    const isGitHubAppError = searchParams.get('github_app_install_error') === '1';
    const installationId = searchParams.get('installation_id');
    const workspaceId = searchParams.get('workspace_id');
    const noState = searchParams.get('no_state') === '1';
    const isRepoConnect = searchParams.get('github_connect') === '1';
    const workspaceSlug = searchParams.get('workspace_slug');

    // ── GitHub App installation (popup / redirect) ──────────────────────
    if (isGitHubAppInstalled || isGitHubAppError) {
      const isPopup = Boolean(window.opener && window.opener !== window);

      if (isPopup) {
        window.opener.postMessage(
          {
            type: isGitHubAppInstalled ? 'github-app-installed' : 'github-app-install-error',
            installationId: installationId ? parseInt(installationId, 10) : null,
            workspaceId: workspaceId ?? null,
            noState,
            error: isGitHubAppError ? searchParams.get('detail') : null,
          },
          window.location.origin
        );
        window.close();
        return;
      }

      if (workspaceId) {
        window.location.href = `/${workspaceId}/repositories`;
      } else {
        window.location.href = '/';
      }
      return;
    }

    // ── OAuth login flow (Google / GitHub sign in) ──────────────────────
    if (!accessToken) {
      setStage('error');
      setError('No access token received. Please try signing in again.');
      return;
    }

    const completeLogin = async () => {
      try {
        useAuthStore.setState({ accessToken });

        const res = await fetch(`${config.api.baseUrl}/auth/me/`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });

        if (!res.ok) {
          throw new Error('Failed to verify session');
        }

        const user: User = await res.json();
        setAuth(user, accessToken);
        setAuthCookie();

        // Fetch workspaces directly — avoids toggling global isLoading
        // which would cause AuthProvider to show its loading screen over this page
        let slug: string | null = null;
        try {
          const page = await workspaceEndpoints.list(20);
          const ws = page.results?.[0];
          if (ws) {
            slug = ws.slug;
            useAuthStore.setState({ workspaces: page.results });
            useAuthStore.getState().setWorkspace(ws.id, ws.slug);
          }
        } catch (wsErr) {
          console.error('Failed to fetch workspaces after OAuth:', wsErr);
        }

        setStage('redirecting');

        setTimeout(() => {
          setLoading(false);
          if (isRepoConnect) {
            router.replace(
              workspaceSlug ? `/${workspaceSlug}/repositories` : slug ? `/${slug}` : '/'
            );
          } else {
            router.replace(slug ? `/${slug}` : '/new-workspace');
          }
        }, 800);
      } catch (err: any) {
        setStage('error');
        setError(err.message || 'Authorization failed');
      }
    };

    completeLogin();
  }, [searchParams]);

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-krait-void">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full opacity-10"
        style={{ background: 'radial-gradient(circle, hsl(var(--primary)) 0%, transparent 70%)' }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-32 -right-32 h-[500px] w-[500px] rounded-full opacity-10"
        style={{
          background: 'radial-gradient(circle, hsl(var(--primary-light)) 0%, transparent 70%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />

      <div className="relative z-10 w-full px-4 py-8">
        <div className="mx-auto w-full max-w-[420px] animate-fade-up">
          <div className="mb-8 text-center">
            <div className="mb-3 inline-flex items-center gap-2">
              <span className="text-2xl font-bold bg-gradient-to-br from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent">
                Kraivor
              </span>
            </div>
          </div>

          <div className="rounded-2xl p-8 bg-krait-surface1 border border-krait-border">
            {stage === 'processing' && (
              <div className="flex flex-col items-center gap-4 py-6">
                <div className="h-10 w-10 animate-spin rounded-full border-2 border-krait-border border-t-[hsl(var(--primary))]" />
                <p className="text-sm text-slate-400">Completing authorization...</p>
              </div>
            )}

            {stage === 'redirecting' && (
              <div className="flex flex-col items-center gap-4 py-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10">
                  <svg
                    className="h-5 w-5 text-emerald-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </div>
                <p className="text-sm text-slate-300 font-medium">Signed in successfully</p>
                <p className="text-xs text-slate-500">Redirecting to dashboard...</p>
              </div>
            )}

            {stage === 'error' && (
              <div className="flex flex-col items-center gap-4 py-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10">
                  <svg
                    className="h-5 w-5 text-red-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <p className="text-sm text-red-300">Authorization failed</p>
                <p className="text-xs text-slate-500 text-center max-w-xs">{error}</p>
                <button
                  onClick={() => router.replace('/login')}
                  className="mt-2 text-xs font-medium text-[hsl(var(--primary-light))] transition-colors hover:text-[hsl(var(--primary))]"
                >
                  Back to sign in
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
