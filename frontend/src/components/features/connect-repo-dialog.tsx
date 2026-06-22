'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  X,
  GitBranch,
  Loader2,
  Search,
  Lock,
  Globe,
  Check,
  AlertCircle,
  Github,
  ExternalLink,
  RefreshCw,
  Settings,
} from 'lucide-react';
import { repositoryEndpoints, type GitHubRepo } from '@/lib/api/endpoints/repositories';
import { useAuthStore } from '@/lib/stores/auth-store';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ConnectRepoDialogProps {
  open: boolean;
  onClose: () => void;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, delay = 400): T {
  const [debounced, setDebounced] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const update = useCallback(
    (v: T) => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setDebounced(v), delay);
    },
    [delay]
  );
  const prev = useRef(value);
  if (prev.current !== value) {
    prev.current = value;
    update(value);
  }
  return debounced;
}

function extractError(err: unknown): { detail: string; code?: string } {
  if (!err || typeof err !== 'object') return { detail: '' };
  const data = (err as any)?.response?.data ?? {};
  return {
    detail: data?.detail ?? (err as any)?.message ?? '',
    code: data?.code,
  };
}

function isGitHubAuthError(err: unknown): boolean {
  const { detail, code } = extractError(err);
  if (code === 'github_app_not_installed' || code === 'github_app_not_configured') return true;
  return (
    detail.toLowerCase().includes('github account') ||
    detail.toLowerCase().includes('no github') ||
    detail.toLowerCase().includes('reconnect') ||
    detail.toLowerCase().includes('token is invalid') ||
    detail.toLowerCase().includes('token has expired')
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ConnectRepoDialog({ open, onClose }: ConnectRepoDialogProps) {
  const workspaceId = useAuthStore(s => s.workspaceId);
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [awaitingPopup, setAwaitingPopup] = useState(false);
  const popupRef = useRef<Window | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const debouncedSearch = useDebounce(search, 400);

  // ── Popup postMessage listener ─────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;

    const handler = async (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;

      const { type, installationId, noState } = event.data ?? {};

      if (type === 'github-app-installed') {
        clearInterval(pollIntervalRef.current);
        setAwaitingPopup(false);

        if (noState && installationId && workspaceId) {
          try {
            await repositoryEndpoints.importInstallation(workspaceId, installationId);
          } catch (err) {
            console.error('[ConnectRepoDialog] Import failed:', err);
          }
        }

        queryClient.invalidateQueries({ queryKey: ['github-installations', workspaceId] });
        queryClient.invalidateQueries({ queryKey: ['github-repos', workspaceId] });
        queryClient.invalidateQueries({ queryKey: ['repos', workspaceId] });
      }

      if (type === 'github-app-install-error') {
        clearInterval(pollIntervalRef.current);
        setAwaitingPopup(false);
        console.error('[ConnectRepoDialog] GitHub App install error:', event.data.error);
      }
    };

    window.addEventListener('message', handler);
    return () => {
      window.removeEventListener('message', handler);
      clearInterval(pollIntervalRef.current);
    };
  }, [open, workspaceId, queryClient]);

  // ── Cleanup on dialog close ────────────────────────────────────────────────
  useEffect(() => {
    if (!open) {
      clearInterval(pollIntervalRef.current);
      setAwaitingPopup(false);
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }
    }
  }, [open]);

  // ── Already-connected repos (mark them disabled in the list) ─────────────
  const { data: connectedRepos = [] } = useQuery({
    queryKey: ['repos', workspaceId],
    queryFn: () => repositoryEndpoints.list(workspaceId!),
    enabled: !!workspaceId && open,
  });

  const connectedSet = new Set(
    (connectedRepos as Array<{ github_repo: string; status: string }>)
      .filter(r => r.status === 'connected')
      .map(r => r.github_repo)
  );

  // ── GitHub repo list from backend (installation-backed) ───────────────────
  const {
    data: githubRepos = [],
    isLoading: reposLoading,
    error: reposError,
    refetch: refetchRepos,
  } = useQuery<GitHubRepo[]>({
    queryKey: ['github-repos', workspaceId, debouncedSearch],
    queryFn: async () => {
      const result = await repositoryEndpoints.listGithubRepos(workspaceId!, debouncedSearch);
      return result as any;
    },
    enabled: !!workspaceId && open,
    staleTime: 30_000,
    retry: false,
  });

  // ── Installations list (used to detect installations and check admin role) ─
  const {
    data: installationsData,
    isLoading: installationsLoading,
    refetch: refetchInstallations,
  } = useQuery({
    queryKey: ['github-installations', workspaceId],
    queryFn: () => repositoryEndpoints.listInstallations(workspaceId!),
    enabled: !!workspaceId && open,
  });

  const installations = installationsData?.installations ?? [];
  const canAdmin = installationsData?.can_admin ?? false;

  // ── Connect a selected repo ───────────────────────────────────────────────
  const { mutate: connectRepo, error: connectError } = useMutation({
    mutationFn: (github_repo: string) => repositoryEndpoints.connect(workspaceId!, { github_repo }),
    onMutate: id => setConnectingId(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos', workspaceId] });
      setConnectingId(null);
      onClose();
    },
    onError: () => setConnectingId(null),
  });

  if (!open) return null;

  // ── Derived state ─────────────────────────────────────────────────────────
  const { detail: reposErrorDetail, code: reposErrorCode } = extractError(reposError);
  const githubNotConnected = isGitHubAuthError(reposError);
  const githubNotConfigured = reposErrorCode === 'github_app_not_configured';
  const hasInstallations = installations.length > 0;

  const connectErrMsg =
    (connectError as any)?.response?.data?.detail ?? (connectError as any)?.message;

  const otherErrMsg =
    !githubNotConnected && reposError
      ? reposErrorDetail || 'Failed to load repositories. Please try again.'
      : null;

  // ── Popup helper ─────────────────────────────────────────────────────────
  const openInstallPopup = (url: string) => {
    const popup = window.open(
      url,
      'github-install',
      'width=1000,height=700,scrollbars=yes,resizable=yes,left=200,top=100'
    );
    if (!popup) {
      window.location.href = url;
      return;
    }
    popupRef.current = popup;
    setAwaitingPopup(true);

    pollIntervalRef.current = setInterval(() => {
      if (popup.closed) {
        clearInterval(pollIntervalRef.current);
        setAwaitingPopup(false);
        refetchInstallations();
        refetchRepos();
        queryClient.invalidateQueries({ queryKey: ['repos', workspaceId] });
      }
    }, 1000);
  };

  const handleConnectGitHub = async () => {
    if (!workspaceId) return;
    try {
      const data = await repositoryEndpoints.installApp(workspaceId);
      if (data.installation_url) {
        openInstallPopup(data.installation_url);
      }
    } catch (err) {
      console.error('[ConnectRepoDialog] Failed to get GitHub App install URL', err);
    }
  };

  const handleConfigure = async (installationId?: number) => {
    if (!workspaceId) return;
    try {
      const data = await repositoryEndpoints.installApp(workspaceId, installationId);
      const url = data.configure_url || data.installation_url;
      if (url) {
        openInstallPopup(url);
      }
    } catch (err) {
      console.error('[ConnectRepoDialog] Failed to get configure URL', err);
    }
  };

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onMouseDown={e => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-lg bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#27272A] shrink-0">
          <h2 className="text-[15px] font-semibold text-[#FAFAFA] flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-venom-yellow" />
            Connect Repository
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-text-tertiary hover:text-[#FAFAFA] transition-colors rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        {installationsLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-5 h-5 animate-spin text-text-tertiary" />
          </div>
        ) : awaitingPopup ? (
          // ── Waiting for popup to complete ─────────────────────────────────
          <div className="flex flex-col items-center justify-center py-10 px-8 text-center gap-5">
            <Loader2 className="w-8 h-8 animate-spin text-venom-yellow" />
            <div className="space-y-1.5">
              <p className="text-[14px] font-semibold text-[#FAFAFA]">
                Waiting for GitHub authorization...
              </p>
              <p className="text-[12px] text-text-tertiary max-w-xs leading-relaxed">
                Complete the authorization in the popup window to continue.
              </p>
            </div>
            <button
              onClick={() => {
                clearInterval(pollIntervalRef.current);
                setAwaitingPopup(false);
                if (popupRef.current && !popupRef.current.closed) {
                  popupRef.current.focus();
                }
              }}
              className="text-[12px] text-venom-yellow hover:underline"
            >
              Click here to refocus the popup
            </button>
          </div>
        ) : githubNotConfigured ? (
          // ── GitHub App not configured on server ───────────────────────────
          <div className="flex flex-col items-center justify-center py-10 px-8 text-center gap-5">
            <div className="w-14 h-14 rounded-full bg-[#1E1E21] border border-[#27272A] flex items-center justify-center">
              <Github className="w-7 h-7 text-[#FAFAFA]" />
            </div>
            <div className="space-y-1.5">
              <p className="text-[14px] font-semibold text-[#FAFAFA]">
                GitHub integration not available
              </p>
              <p className="text-[12px] text-text-tertiary max-w-xs leading-relaxed">
                The GitHub App integration has not been configured on this server. Contact your
                administrator to set it up.
              </p>
            </div>
          </div>
        ) : githubNotConnected ? (
          // ── GitHub App not installed (admin only — non-admins get 200 []) ─
          <div className="flex flex-col items-center justify-center py-10 px-8 text-center gap-5">
            <div className="w-14 h-14 rounded-full bg-[#1E1E21] border border-[#27272A] flex items-center justify-center">
              <Github className="w-7 h-7 text-[#FAFAFA]" />
            </div>

            <div className="space-y-1.5">
              <p className="text-[14px] font-semibold text-[#FAFAFA]">Authorize GitHub access</p>
              <p className="text-[12px] text-text-tertiary max-w-xs leading-relaxed">
                Kraivor needs access to your GitHub repositories. You'll be redirected to GitHub to
                grant access — choose all repositories or select specific ones.
              </p>
            </div>

            <div className="w-full bg-[#0A0A0B] border border-[#27272A] rounded-lg divide-y divide-[#27272A] text-left">
              {[
                { icon: '📂', label: 'Repository access', sub: 'Read your repositories' },
                { icon: '👤', label: 'Account information', sub: 'Read your public profile' },
                { icon: '📧', label: 'Email addresses', sub: 'Read your verified emails' },
              ].map(item => (
                <div key={item.label} className="flex items-center gap-3 px-3 py-2.5">
                  <span className="text-base">{item.icon}</span>
                  <div>
                    <p className="text-[12px] font-medium text-[#FAFAFA]">{item.label}</p>
                    <p className="text-[11px] text-text-tertiary">{item.sub}</p>
                  </div>
                  <Check className="ml-auto w-3.5 h-3.5 text-green-500 shrink-0" />
                </div>
              ))}
            </div>

            <button
              onClick={handleConnectGitHub}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#FAFAFA] text-black text-[13px] font-semibold rounded-lg hover:bg-white transition-colors"
            >
              <Github className="w-4 h-4" />
              Authorize with GitHub
              <ExternalLink className="w-3 h-3 opacity-50" />
            </button>

            <p className="text-[10px] text-text-tertiary">
              You'll be redirected to GitHub. After granting access you'll return here
              automatically.
            </p>
          </div>
        ) : !canAdmin ? (
          // ── Non-admin — show only already-connected repos ─────────────────
          <div className="flex-1 overflow-y-auto px-2 pb-3 min-h-0">
            {connectedSet.size > 0 ? (
              <ul className="space-y-0.5 mt-1">
                {Array.from(connectedSet).map(repoFullName => (
                  <li key={repoFullName}>
                    <div className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg opacity-60 cursor-default">
                      <div className="shrink-0 w-7 h-7 rounded-md bg-[#1E1E21] border border-[#27272A] flex items-center justify-center">
                        <GitBranch className="w-3.5 h-3.5 text-text-tertiary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-[13px] font-medium text-[#FAFAFA] truncate block">
                          {repoFullName}
                        </span>
                      </div>
                      <Check className="w-3.5 h-3.5 text-green-500 shrink-0" />
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
                <GitBranch className="w-8 h-8 text-text-tertiary mb-1" />
                <p className="text-[13px] text-text-secondary">No repositories connected yet.</p>
                <p className="text-[11px] text-text-tertiary max-w-xs">
                  Only workspace admins can connect GitHub repositories.
                </p>
              </div>
            )}
          </div>
        ) : (
          // ── Admin — show full repo picker with configure options ─────────
          <>
            {/* Search + Configure row */}
            <div className="px-4 pt-4 pb-2 shrink-0 space-y-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search repositories..."
                  autoFocus
                  className="w-full pl-9 pr-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors"
                />
              </div>

              {hasInstallations && (
                <div className="flex items-center justify-end px-1">
                  <button
                    onClick={() => handleConfigure()}
                    className="text-[11px] text-venom-yellow hover:text-venom-yellow/80 hover:underline transition-colors"
                  >
                    GitHub App permissions
                  </button>
                </div>
              )}
            </div>

            {/* Error banners */}
            {otherErrMsg && (
              <div className="mx-4 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-[12px] text-red-400 shrink-0">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span className="flex-1">{otherErrMsg}</span>
                <button onClick={() => refetchRepos()} className="shrink-0 hover:text-red-300">
                  <RefreshCw className="w-3 h-3" />
                </button>
              </div>
            )}
            {connectErrMsg && (
              <div className="mx-4 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2 text-[12px] text-red-400 shrink-0">
                <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                {connectErrMsg}
              </div>
            )}

            {/* Repo list */}
            <div className="flex-1 overflow-y-auto px-2 pb-3 min-h-0">
              {reposLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-5 h-5 animate-spin text-text-tertiary" />
                </div>
              ) : githubRepos.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
                  <GitBranch className="w-8 h-8 text-text-tertiary mb-1" />
                  <p className="text-[13px] text-text-secondary">
                    {search
                      ? 'No repositories match your search.'
                      : hasInstallations
                        ? 'No repositories available from your GitHub accounts.'
                        : 'No repositories found.'}
                  </p>
                  {hasInstallations && (
                    <p className="text-[11px] text-text-tertiary max-w-xs">
                      Select additional repositories on GitHub.
                    </p>
                  )}
                  {hasInstallations &&
                    installations.map(inst => (
                      <button
                        key={inst.id}
                        onClick={() => handleConfigure(inst.installation_id)}
                        className="flex items-center gap-2 px-4 py-2 border border-[#27272A] rounded-lg text-[12px] text-text-secondary hover:text-[#FAFAFA] hover:border-[#FAFAFA]/30 transition-colors"
                      >
                        <Settings className="w-3.5 h-3.5" />
                        Configure {inst.github_account_login}
                        <ExternalLink className="w-3 h-3 opacity-50" />
                      </button>
                    ))}
                </div>
              ) : (
                <ul className="space-y-0.5 mt-1">
                  {githubRepos.map(repo => {
                    const isConnected = connectedSet.has(repo.full_name);
                    const isConnecting = connectingId === repo.full_name;

                    return (
                      <li key={repo.full_name}>
                        <button
                          disabled={isConnected || isConnecting}
                          onClick={() => connectRepo(repo.full_name)}
                          className={[
                            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                            isConnected
                              ? 'opacity-40 cursor-not-allowed'
                              : 'hover:bg-[#1E1E21] cursor-pointer',
                          ].join(' ')}
                        >
                          <div className="shrink-0 w-7 h-7 rounded-md bg-[#1E1E21] border border-[#27272A] flex items-center justify-center">
                            <GitBranch className="w-3.5 h-3.5 text-text-tertiary" />
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[13px] font-medium text-[#FAFAFA] truncate">
                                {repo.full_name}
                              </span>
                              <span className="shrink-0 flex items-center gap-0.5 text-[10px] text-text-tertiary bg-[#27272A] px-1.5 py-0.5 rounded">
                                {repo.private ? (
                                  <>
                                    <Lock className="w-2.5 h-2.5" /> Private
                                  </>
                                ) : (
                                  <>
                                    <Globe className="w-2.5 h-2.5" /> Public
                                  </>
                                )}
                              </span>
                            </div>
                            {repo.description && (
                              <p className="text-[11px] text-text-tertiary truncate mt-0.5">
                                {repo.description}
                              </p>
                            )}
                            {repo.language && (
                              <span className="text-[10px] text-text-tertiary mt-0.5 inline-block">
                                {repo.language}
                              </span>
                            )}
                          </div>

                          <div className="shrink-0 w-6 flex justify-end">
                            {isConnecting ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-venom-yellow" />
                            ) : isConnected ? (
                              <Check className="w-3.5 h-3.5 text-green-500" />
                            ) : null}
                          </div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </>
        )}

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#27272A] shrink-0 flex items-center justify-between">
          <p className="text-[11px] text-text-tertiary">
            {awaitingPopup
              ? 'Waiting for GitHub authorization...'
              : githubNotConfigured
                ? 'GitHub integration not configured'
                : githubNotConnected
                  ? 'GitHub authorization required'
                  : !canAdmin
                    ? connectedSet.size > 0
                      ? `${connectedSet.size} repo${connectedSet.size > 1 ? 's' : ''} connected`
                      : 'No repositories connected'
                    : connectedSet.size > 0
                      ? `${connectedSet.size} repo${connectedSet.size > 1 ? 's' : ''} already connected`
                      : hasInstallations
                        ? 'Select a repository or manage access'
                        : 'Click a repository to connect it'}
          </p>
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-[12px] text-text-secondary hover:text-[#FAFAFA] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
