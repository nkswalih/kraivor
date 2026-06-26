'use client';

import { useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeft, GitBranch, Loader2, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import type { Repository } from '@/types/api';
import { useQuery } from '@tanstack/react-query';
import { repositoryEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useStartAnalysis } from '@/lib/hooks/use-analysis';
import type { StartAnalysisRequest } from '@/types/domain/analysis';

export default function NewAnalysisPage() {
  const router = useRouter();
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore((s) => s.workspaceId);

  const [repoId, setRepoId] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [deepScan, setDeepScan] = useState(false);
  const [depth, setDepth] = useState(1);

  const { data: repos, isLoading: reposLoading, error: reposError } = useQuery<Repository[]>({
    queryKey: ['repos', workspaceId],
    queryFn: () => repositoryEndpoints.list(workspaceId!),
    enabled: !!workspaceId,
  });

  const reposList = repos ?? [];

  const { mutate: startAnalysis, isPending, error: startError } = useStartAnalysis();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoId || !workspaceId) return;

    const data: StartAnalysisRequest = {
      repo_id: repoId,
      workspace_id: workspaceId,
      repo_url: repoUrl,
      branch,
      deep_scan: deepScan,
      depth: deepScan ? depth : 1,
    };

    startAnalysis(data, {
      onSuccess: (job) => {
        router.push(`/${workspaceSlug}/analysis/jobs/${job.job_id}`);
      },
    });
  };

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center gap-3 mb-1">
          <Link
            href={`/${workspaceSlug}/analysis`}
            className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground">New Analysis</h1>
        </div>
        <p className="text-sm text-text-tertiary mt-1">Configure and start a repository analysis</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Repository Selection */}
          <div>
            <label className="text-[13px] font-medium text-foreground block mb-1.5">
              Repository
            </label>
            {reposLoading ? (
              <div className="flex items-center gap-2 text-text-tertiary text-[13px] p-3 border border-border rounded-md bg-card">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading repositories...
              </div>
            ) : reposError ? (
              <div className="flex items-center gap-2 text-color-error text-[13px] p-3 border border-border rounded-md bg-card">
                <AlertCircle className="w-4 h-4" />
                Failed to load repositories
              </div>
            ) : reposList.length === 0 ? (
              <div className="p-3 border border-border rounded-md bg-card text-text-tertiary text-[13px]">
                No repositories found. Connect one first.
              </div>
            ) : (
              <select
                value={repoId}
                onChange={(e) => {
                  const id = e.target.value;
                  setRepoId(id);
                  const r = reposList.find((r: { id: string }) => r.id === id);
                  if (r) {
                    setRepoUrl(`https://github.com/${r.github_repo}` || '');
                  }
                }}
                className="w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none transition-colors"
                required
              >
                <option value="">Select a repository...</option>
                {reposList.map((r: Repository) => (
                  <option key={r.id} value={r.id}>
                    {r.github_repo || r.id}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Branch */}
          <div>
            <label className="text-[13px] font-medium text-foreground block mb-1.5">
              Branch
            </label>
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              className="w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none transition-colors"
              placeholder="main"
            />
          </div>

          {/* Deep Scan Toggle */}
          <div className="flex items-center justify-between p-3 border border-border rounded-md bg-card">
            <div>
              <p className="text-[13px] font-medium text-foreground">Deep Scan</p>
              <p className="text-[12px] text-text-tertiary">Analyze entire commit history and nested directories</p>
            </div>
            <button
              type="button"
              onClick={() => setDeepScan(!deepScan)}
              className={`relative w-10 h-5 rounded-full transition-colors ${deepScan ? 'bg-yellow-500' : 'bg-krait-surface3'}`}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${deepScan ? 'translate-x-5' : 'translate-x-0.5'}`}
              />
            </button>
          </div>

          {/* Depth (shown only when deep scan is on) */}
          {deepScan && (
            <div>
              <label className="text-[13px] font-medium text-foreground block mb-1.5">
                Scan Depth (1-10)
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={depth}
                onChange={(e) => setDepth(Math.min(10, Math.max(1, Number(e.target.value))))}
                className="w-full bg-card border border-border rounded-md px-3 py-2 text-[13px] text-foreground focus:border-primary focus:outline-none transition-colors"
              />
            </div>
          )}

          {/* Error */}
          {startError && (
            <div className="flex items-center gap-2 p-3 border border-red-500/30 bg-red-500/10 rounded-md text-color-error text-[13px]">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {startError.message}
            </div>
          )}

          {/* Submit */}
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={isPending || !repoId || !workspaceId}
              className="flex items-center gap-2 px-5 py-2 rounded-md btn-shimmer text-primary-foreground text-[13px] font-semibold disabled:opacity-50 transition-all active:scale-[0.98]"
            >
              {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitBranch className="w-4 h-4" />}
              {isPending ? 'Starting...' : 'Start Analysis'}
            </button>
            <Link
              href={`/${workspaceSlug}/analysis`}
              className="px-5 py-2 rounded-md border border-border bg-card text-text-secondary text-[13px] font-medium hover:text-foreground transition-colors"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
