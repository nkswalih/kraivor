'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Activity, Plus, GitBranch, Clock, Search, Filter, Loader2, AlertCircle } from 'lucide-react';
import { useJobsList } from '@/lib/hooks/use-analysis';
import { useAuthStore } from '@/lib/stores/auth-store';
import { JobStatusBadge } from '@/components/analysis/job-status-badge';
import { ProgressBar } from '@/components/analysis/progress-bar';
import { Skeleton } from '@/components/ui/shadcn';
import { formatRelativeTime } from '@/lib/utils';
import type { AnalysisJob } from '@/types/domain/analysis';

function JobRow({ job, workspaceSlug }: { job: AnalysisJob; workspaceSlug: string }) {
  const isRunning = !['completed', 'failed'].includes(job.status);
  return (
    <Link
      href={`/${workspaceSlug}/analysis/jobs/${job.job_id}`}
      className="grid grid-cols-[100px_1.5fr_1fr_1fr_1fr_100px] gap-4 p-3 items-center hover:bg-white/[0.02] transition-colors text-[13px] group border-b border-border last:border-0"
    >
      <JobStatusBadge status={job.status} className="justify-self-start" />
      <div className="flex items-center gap-2 min-w-0">
        <GitBranch className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        <span className="text-foreground truncate">
          {job.repo_url?.replace('https://github.com/', '') || job.repo_id.slice(0, 8)}
        </span>
      </div>
      <div className="text-muted-foreground text-[12px] font-mono">{job.branch}</div>
      <div>
        {isRunning ? (
          <ProgressBar pct={job.progress_pct} message={job.progress_message} />
        ) : job.overall_score != null ? (
          <span className="text-foreground font-semibold">{job.overall_score}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </div>
      <div className="text-muted-foreground text-[12px]">{job.total_findings}</div>
      <div className="text-muted-foreground text-[12px] font-mono flex items-center gap-1">
        <Clock className="w-3 h-3" />
        {formatRelativeTime(job.created_at)}
      </div>
    </Link>
  );
}

export default function AnalysisPage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore((s) => s.workspaceId);
  const [page, setPage] = useState(1);
  const { data, isLoading, error } = useJobsList(page, 20, workspaceId ?? undefined);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <AlertCircle className="w-10 h-10 text-color-error mb-3" />
        <p className="text-base font-medium text-text-primary mb-1">Failed to load analyses</p>
        <p className="text-sm text-text-tertiary">{error.message}</p>
      </div>
    );
  }

  const jobs = data?.jobs ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  const stats = {
    total,
    completed: jobs.filter((j: AnalysisJob) => j.status === 'completed').length,
    failed: jobs.filter((j: AnalysisJob) => j.status === 'failed').length,
    inProgress: jobs.filter((j: AnalysisJob) => !['completed', 'failed'].includes(j.status)).length,
  };

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-medium flex items-center gap-2 text-foreground">
            <Activity className="w-5 h-5 text-primary" /> Repository Analysis
          </h1>
          <Link
            href={`/${workspaceSlug}/analysis/new`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md btn-shimmer text-primary-foreground text-[12px] font-semibold transition-all active:scale-[0.98]"
          >
            <Plus className="w-3.5 h-3.5" />
            New Analysis
          </Link>
        </div>

        {!isLoading && jobs.length > 0 && (
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-card border border-border rounded-lg p-3">
              <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Total</p>
              <p className="text-xl font-semibold text-foreground mt-1">{stats.total}</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-3">
              <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Completed</p>
              <p className="text-xl font-semibold text-green-400 mt-1">{stats.completed}</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-3">
              <p className="text-[11px] text-text-tertiary uppercase tracking-wider">In Progress</p>
              <p className="text-xl font-semibold text-yellow-400 mt-1">{stats.inProgress}</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-3">
              <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Failed</p>
              <p className="text-xl font-semibold text-red-400 mt-1">{stats.failed}</p>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search analyses..."
              className="w-[200px] bg-card border border-border text-[12px] text-foreground rounded-md pl-8 pr-3 py-1.5 focus:border-primary focus:outline-none transition-colors"
            />
          </div>
          <button className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors">
            <Filter className="w-3.5 h-3.5" />
          </button>
          {isLoading && <Loader2 className="w-4 h-4 text-venom-yellow animate-spin ml-auto" />}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-background p-6">
        {isLoading && jobs.length === 0 ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-lg" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Activity className="w-10 h-10 text-text-tertiary mb-3" />
            <p className="text-base font-medium text-text-primary mb-1">No analyses yet</p>
            <p className="text-sm text-text-tertiary mb-4 max-w-sm">
              Run your first analysis to check repository health, find issues, and get performance insights.
            </p>
            <Link
              href={`/${workspaceSlug}/analysis/new`}
              className="flex items-center gap-2 px-4 py-2 rounded-md btn-shimmer text-primary-foreground text-[13px] font-semibold"
            >
              <Plus className="w-4 h-4" />
              Run First Analysis
            </Link>
          </div>
        ) : (
          <>
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="grid grid-cols-[100px_1.5fr_1fr_1fr_1fr_100px] gap-4 p-3 border-b border-border bg-background/50 text-[12px] font-medium text-muted-foreground">
                <div>Status</div>
                <div>Repository</div>
                <div>Branch</div>
                <div>Score</div>
                <div>Findings</div>
                <div>Date</div>
              </div>
              <div className="divide-y divide-border">
                {jobs.map((job: AnalysisJob) => (
                  <JobRow key={job.job_id} job={job} workspaceSlug={workspaceSlug} />
                ))}
              </div>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <span className="text-[12px] text-muted-foreground">
                  Page {page} of {totalPages} ({total} total)
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page <= 1}
                    className="px-3 py-1 text-[12px] border border-border rounded-md bg-card text-foreground disabled:opacity-30 hover:bg-white/5 transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page >= totalPages}
                    className="px-3 py-1 text-[12px] border border-border rounded-md bg-card text-foreground disabled:opacity-30 hover:bg-white/5 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
