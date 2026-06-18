'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GitBranch, Plus, MoreHorizontal, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { repositoryEndpoints } from '@/lib/api/endpoints';
import { ConnectRepoDialog } from '@/components/features/connect-repo-dialog';
import { SkeletonTable, SkeletonCard, SkeletonBlock, SkeletonLine } from '@/components/ui/skeletons';

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
          <SkeletonLine className="w-32 h-5" />
          <SkeletonBlock className="w-28 h-8 rounded" />
        </div>
        <div className="flex-1 p-6">
          <SkeletonTable rows={4} />
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
          className="bg-venom-yellow hover:bg-primary-light text-black text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Connect Repo
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {(!repos || repos.length === 0) ? (
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
            <div className="grid grid-cols-[2fr_1fr_1fr_100px] gap-4 p-3 border-b border-krait-border bg-krait-surface2 text-[12px] font-medium text-text-tertiary">
              <div>Repository Name</div>
              <div>Status</div>
              <div>Language</div>
              <div></div>
            </div>
            <div className="divide-y divide-krait-border text-[13px]">
              {repos.map((repo) => (
                <div key={repo.id} className="grid grid-cols-[2fr_1fr_1fr_100px] gap-4 p-3 items-center hover:bg-krait-surface2/50 transition-colors cursor-pointer">
                  <div className="flex items-center gap-2 font-medium text-text-primary">
                    <GitBranch className="w-4 h-4 text-text-tertiary" />
                    {repo.github_repo}
                  </div>
                  <div className="flex items-center gap-1.5 text-text-secondary">
                    <span className={`w-1.5 h-1.5 rounded-full ${repo.status === 'connected' ? 'bg-green-500' : 'bg-text-tertiary'}`} />
                    {repo.status === 'connected' ? 'Connected' : 'Disconnected'}
                  </div>
                  <div>
                    <span className="text-text-secondary">{repo.language ?? '—'}</span>
                  </div>
                  <div className="flex justify-end">
                    <button className="p-1 hover:bg-krait-surface3 rounded text-text-tertiary hover:text-text-primary">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <ConnectRepoDialog open={showConnect} onClose={() => setShowConnect(false)} />
    </div>
  );
}
