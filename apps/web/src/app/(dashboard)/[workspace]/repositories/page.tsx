'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GitBranch, Plus, MoreHorizontal, Loader2, ExternalLink, Clock, Github } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { repositoryEndpoints } from '@/lib/api/endpoints';
import { ConnectRepoDialog } from '@/components/features/connect-repo-dialog';
import { Skeleton } from '@/components/ui/shadcn/skeleton';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/shadcn/avatar';
import { Badge } from '@/components/ui/shadcn/badge';
import { formatRelativeTime } from '@/lib/utils';
import type { Repository } from '@/types/api';

function RepoRowSkeleton() {
  return (
    <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_40px] gap-4 p-3 items-center border-b border-krait-border">
      <div className="flex items-center gap-2.5">
        <Skeleton className="w-4 h-4 rounded" />
        <Skeleton className="h-4 w-32 rounded" />
      </div>
      <div className="flex items-center gap-2">
        <Skeleton className="w-6 h-6 rounded-full" />
        <Skeleton className="h-3.5 w-16 rounded" />
      </div>
      <Skeleton className="h-5 w-20 rounded-full" />
      <Skeleton className="h-3.5 w-12 rounded" />
      <Skeleton className="h-3.5 w-14 rounded" />
      <Skeleton className="h-3.5 w-12 rounded" />
      <div />
    </div>
  );
}

function getRepoOwner(githubRepo: string): string {
  return githubRepo.split('/')[0] ?? githubRepo;
}

function getRepoName(githubRepo: string): string {
  return githubRepo.split('/')[1] ?? githubRepo;
}

function getGithubUrl(githubRepo: string): string {
  return `https://github.com/${githubRepo}`;
}

function getAvatarUrl(owner: string): string {
  return `https://github.com/${owner}.png?size=40`;
}

export default function RepositoriesPage() {
  const workspaceId = useAuthStore(s => s.workspaceId);
  const [showConnect, setShowConnect] = useState(false);

  const { data: repos, isLoading } = useQuery({
    queryKey: ['repos', workspaceId],
    queryFn: () => repositoryEndpoints.list(workspaceId!),
    enabled: !!workspaceId,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full animate-fade-up">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <Skeleton className="w-32 h-5 rounded" />
          <Skeleton className="w-28 h-8 rounded" />
        </div>
        <div className="flex-1 p-6">
          <div className="border border-krait-border rounded-lg bg-krait-surface1 overflow-hidden">
            <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_40px] gap-4 p-3 border-b border-krait-border bg-krait-surface2">
              {Array.from({ length: 7 }).map((_, i) => (
                <Skeleton key={i} className="h-3.5 w-16 rounded" />
              ))}
            </div>
            <div className="divide-y divide-krait-border">
              {Array.from({ length: 4 }).map((_, i) => (
                <RepoRowSkeleton key={i} />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <h1 className="text-lg font-medium flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-venom-yellow" /> Repositories
        </h1>
        <button
          onClick={() => setShowConnect(true)}
          className="bg-venom-yellow hover:bg-primary-light text-black text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5 transition-colors active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" /> Connect Repo
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {!repos || repos.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <GitBranch className="w-10 h-10 text-muted-foreground mb-3" />
            <h3 className="text-base font-medium text-foreground mb-1">No repositories</h3>
            <p className="text-[13px] text-muted-foreground max-w-xs mb-4">
              Connect a GitHub repository to start analyzing your codebase.
            </p>
            <button
              onClick={() => setShowConnect(true)}
              className="btn-shimmer text-text-inverse text-[12px] font-medium py-2 px-4 rounded flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" /> Connect Repository
            </button>
          </div>
        ) : (
          <div className="border border-krait-border rounded-lg bg-krait-surface1 overflow-hidden">
            <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_40px] gap-4 p-3 border-b border-krait-border bg-krait-surface2 text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
              <div>Repository</div>
              <div>Author</div>
              <div>Status</div>
              <div>Branch</div>
              <div>Language</div>
              <div>Connected</div>
              <div />
            </div>
            <div className="divide-y divide-krait-border text-[13px]">
              {repos.map(repo => {
                const owner = getRepoOwner(repo.github_repo);
                const name = getRepoName(repo.github_repo);
                const githubUrl = getGithubUrl(repo.github_repo);
                const avatarUrl = getAvatarUrl(owner);
                return (
                  <div
                    key={repo.id}
                    className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,0.7fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_40px] gap-4 p-3 items-center hover:bg-krait-surface2/50 transition-colors"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Github className="w-4 h-4 text-text-tertiary shrink-0" />
                      <div className="min-w-0">
                        <a
                          href={githubUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-text-primary hover:text-venom-yellow transition-colors truncate block"
                        >
                          {name}
                        </a>
                        {repo.description && (
                          <p className="text-[11px] text-text-tertiary truncate mt-0.5 leading-tight">
                            {repo.description}
                          </p>
                        )}
                      </div>
                      <a
                        href={githubUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 ml-auto text-text-tertiary hover:text-text-primary transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>

                    <div className="flex items-center gap-2 min-w-0">
                      <Avatar className="w-6 h-6 shrink-0">
                        <AvatarImage src={avatarUrl} alt={owner} />
                        <AvatarFallback className="text-[10px] bg-krait-surface3 text-text-secondary">
                          {owner.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <span className="text-text-secondary truncate">{owner}</span>
                    </div>

                    <div>
                      <Badge
                        variant={repo.status === 'connected' ? 'success' : 'default'}
                        className="capitalize"
                      >
                        {repo.status}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-1.5 min-w-0">
                      <GitBranch className="w-3 h-3 text-text-tertiary shrink-0" />
                      <span className="text-text-secondary text-[12px] font-mono truncate">
                        {repo.default_branch}
                      </span>
                    </div>

                    <div>
                      <span className="text-text-secondary">{repo.language ?? '—'}</span>
                    </div>

                    <div className="flex items-center gap-1.5 text-text-tertiary">
                      <Clock className="w-3.5 h-3.5 shrink-0" />
                      <span className="text-[12px]">{formatRelativeTime(repo.created_at)}</span>
                    </div>

                    <div className="flex justify-end">
                      <button className="p-1 hover:bg-krait-surface3 rounded text-text-tertiary hover:text-text-primary transition-colors">
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <ConnectRepoDialog open={showConnect} onClose={() => setShowConnect(false)} />
    </div>
  );
}
