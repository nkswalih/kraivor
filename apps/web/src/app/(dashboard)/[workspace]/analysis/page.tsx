'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Activity, Plus, GitBranch, Clock, Search, Loader2, AlertCircle, Trash2,
  ExternalLink, BarChart3, CheckCircle2, XCircle, ChevronRight, ChevronDown,
  Bug, FilterX, Layers,
} from 'lucide-react';
import { toast } from 'sonner';
import { useJobsList, useDeleteJob } from '@/lib/hooks/use-analysis';
import { useAuthStore } from '@/lib/stores/auth-store';
import { JobStatusBadge } from '@/components/analysis/job-status-badge';
import { ProgressBar } from '@/components/analysis/progress-bar';
import { Skeleton } from '@/components/ui/shadcn';
import { formatRelativeTime } from '@/lib/utils';
import type { AnalysisJob, JobStatus } from '@/types/domain/analysis';

type StatusFilter = 'all' | 'completed' | 'failed' | 'running';

function getRepoName(repoUrl: string): string {
  return repoUrl?.replace('https://github.com/', '') || '';
}

function getRepoKey(job: AnalysisJob): string {
  return job.repo_url || job.repo_id;
}

function getRepoDisplayName(job: AnalysisJob): string {
  return getRepoName(job.repo_url) || job.repo_id.slice(0, 12);
}

function getFindingsColor(count: number): string {
  if (count === 0) return 'text-text-tertiary';
  if (count < 10) return 'text-green-400';
  if (count < 50) return 'text-yellow-400';
  return 'text-red-400';
}

function getFindingsBg(count: number): string {
  if (count === 0) return 'bg-krait-surface2';
  if (count < 10) return 'bg-green-500/10';
  if (count < 50) return 'bg-yellow-500/10';
  return 'bg-red-500/10';
}

const FILTER_TABS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'completed', label: 'Completed' },
  { key: 'running', label: 'Running' },
  { key: 'failed', label: 'Failed' },
];

function JobGroupSkeleton() {
  return (
    <div className="border border-krait-border rounded-lg bg-krait-surface1 overflow-hidden">
      <div className="flex items-center gap-3 p-3.5 bg-krait-surface2 border-b border-krait-border">
        <Skeleton className="w-4 h-4 rounded" />
        <Skeleton className="h-4 w-48 rounded" />
        <Skeleton className="h-5 w-16 rounded-full ml-auto" />
      </div>
      <div className="divide-y divide-krait-border">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,0.65fr)_minmax(0,0.8fr)_minmax(0,0.55fr)_minmax(0,0.55fr)_36px] gap-4 p-3.5 items-center border-b border-krait-border last:border-0">
            <Skeleton className="h-4 w-36 rounded" />
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-4 w-24 rounded" />
            <Skeleton className="h-4 w-12 rounded" />
            <Skeleton className="h-3.5 w-14 rounded" />
            <div />
          </div>
        ))}
      </div>
    </div>
  );
}

function JobRow({ job, workspaceSlug }: { job: AnalysisJob; workspaceSlug: string }) {
  const isRunning = !['completed', 'failed'].includes(job.status);
  const deleteJob = useDeleteJob();
  const [deleting, setDeleting] = useState(false);
  const repoName = getRepoName(job.repo_url);

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (deleting) return;
    setDeleting(true);
    try {
      await deleteJob.mutateAsync(job.job_id);
      toast.success('Analysis deleted');
    } catch {
      toast.error('Failed to delete analysis');
    } finally {
      setDeleting(false);
    }
  };

  const scoreColor =
    job.overall_score != null
      ? job.overall_score >= 80
        ? 'text-green-400'
        : job.overall_score >= 50
          ? 'text-yellow-400'
          : 'text-red-400'
      : 'text-text-tertiary';

  const findingsCount = job.total_findings ?? 0;

  return (
    <Link
      href={`/${workspaceSlug}/analysis/jobs/${job.job_id}`}
      className="grid grid-cols-[minmax(0,1.2fr)_minmax(0,0.65fr)_minmax(0,0.8fr)_minmax(0,0.55fr)_minmax(0,0.55fr)_36px] gap-4 p-3.5 items-center hover:bg-krait-surface2/50 transition-colors text-[13px] group border-b border-krait-border last:border-0"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <GitBranch className="w-4 h-4 text-text-tertiary shrink-0" />
        <div className="min-w-0">
          <span className="text-text-primary truncate block leading-tight">
            {repoName || job.repo_id.slice(0, 8)}
          </span>
          <span className="text-[11px] text-text-tertiary font-mono truncate block mt-0.5">
            {job.branch}
          </span>
        </div>
        {job.repo_url && (
          <span
            onClick={e => {
              e.preventDefault();
              e.stopPropagation();
              window.open(job.repo_url, '_blank', 'noopener,noreferrer');
            }}
            className="shrink-0 ml-auto text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
          >
            <ExternalLink className="w-3 h-3" />
          </span>
        )}
      </div>

      <JobStatusBadge status={job.status as JobStatus} />

      <div className="min-w-0">
        {isRunning ? (
          <ProgressBar pct={job.progress_pct} message={job.progress_message} />
        ) : job.overall_score != null ? (
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${scoreColor}`}>{job.overall_score}</span>
            <div className="flex-1 h-1.5 bg-krait-surface2 rounded-full overflow-hidden max-w-[60px]">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(100, Math.max(0, job.overall_score))}%`,
                  background:
                    job.overall_score >= 80
                      ? 'linear-gradient(90deg, #22c55e, #16a34a)'
                      : job.overall_score >= 50
                        ? 'linear-gradient(90deg, #eab308, #f59e0b)'
                        : 'linear-gradient(90deg, #ef4444, #dc2626)',
                }}
              />
            </div>
          </div>
        ) : (
          <span className="text-text-tertiary">—</span>
        )}
      </div>

      <div>
        <span
          className={`inline-flex items-center gap-1.5 text-[12px] font-medium px-2 py-0.5 rounded-md ${getFindingsBg(findingsCount)} ${getFindingsColor(findingsCount)}`}
        >
          <Bug className="w-3 h-3" />
          {findingsCount}
        </span>
      </div>

      <div className="flex items-center gap-1.5 text-text-tertiary">
        <Clock className="w-3 h-3 shrink-0" />
        <span className="text-[12px] whitespace-nowrap">{formatRelativeTime(job.created_at)}</span>
      </div>

      <button
        onClick={handleDelete}
        disabled={deleting}
        className="p-1.5 rounded-md text-text-tertiary hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-30"
        title="Delete this analysis"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </Link>
  );
}

function JobGroup({
  repoKey,
  jobs,
  workspaceSlug,
}: {
  repoKey: string;
  jobs: AnalysisJob[];
  workspaceSlug: string;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const latest = jobs[0];
  const isRunning = !['completed', 'failed'].includes(latest.status);
  const bestScore = Math.max(...jobs.map(j => j.overall_score ?? 0));
  const worstScore = Math.min(...jobs.map(j => j.overall_score ?? 100));

  return (
    <div className="border border-krait-border rounded-lg bg-krait-surface1 overflow-hidden">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-3 w-full p-3.5 bg-krait-surface2 border-b border-krait-border text-left hover:bg-krait-surface3/50 transition-colors"
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4 text-text-tertiary shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text-tertiary shrink-0" />
        )}
        <Layers className="w-4 h-4 text-text-tertiary shrink-0" />
        <span className="text-text-primary font-medium text-[13px]">
          {getRepoDisplayName(latest)}
        </span>
        <div className="flex items-center gap-2 ml-auto">
          {!isRunning && bestScore > 0 && (
            <span className={`text-[12px] font-semibold tabular-nums ${
              bestScore >= 80 ? 'text-green-400' : bestScore >= 50 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {bestScore}
              {worstScore !== bestScore && `–${worstScore}`}
            </span>
          )}
          <span className="text-[11px] text-text-tertiary bg-krait-surface3 px-2 py-0.5 rounded-full font-medium tabular-nums">
            {jobs.length} run{jobs.length !== 1 && 's'}
          </span>
          <JobStatusBadge status={latest.status as JobStatus} />
        </div>
      </button>
      {!collapsed && (
        <div className="divide-y divide-krait-border">
          {jobs.map(job => (
            <JobRow key={job.job_id} job={job} workspaceSlug={workspaceSlug} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AnalysisPage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore((s) => s.workspaceId);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const { data, isLoading, error } = useJobsList(page, 50, workspaceId ?? undefined);

  const allJobs = data?.jobs ?? [];
  const total = data?.total ?? 0;

  const filteredJobs = useMemo(() => {
    let result = allJobs;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        j =>
          (j.repo_url?.toLowerCase().includes(q)) ||
          j.repo_id.toLowerCase().includes(q) ||
          j.branch?.toLowerCase().includes(q),
      );
    }

    if (statusFilter === 'completed') {
      result = result.filter(j => j.status === 'completed');
    } else if (statusFilter === 'failed') {
      result = result.filter(j => j.status === 'failed');
    } else if (statusFilter === 'running') {
      result = result.filter(j => !['completed', 'failed'].includes(j.status));
    }

    return result;
  }, [allJobs, searchQuery, statusFilter]);

  const groupedJobs = useMemo(() => {
    const groups = new Map<string, AnalysisJob[]>();
    for (const job of filteredJobs) {
      const key = getRepoKey(job);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(job);
    }
    return Array.from(groups.entries()).sort((a, b) => {
      const aLatest = a[1][0]?.created_at ?? '';
      const bLatest = b[1][0]?.created_at ?? '';
      return bLatest.localeCompare(aLatest);
    });
  }, [filteredJobs]);

  const stats = useMemo(() => ({
    total,
    completed: allJobs.filter((j: AnalysisJob) => j.status === 'completed').length,
    failed: allJobs.filter((j: AnalysisJob) => j.status === 'failed').length,
    inProgress: allJobs.filter((j: AnalysisJob) => !['completed', 'failed'].includes(j.status)).length,
  }), [allJobs, total]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <AlertCircle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-base font-medium text-text-primary mb-1">Failed to load analyses</p>
        <p className="text-sm text-text-tertiary">{error.message}</p>
      </div>
    );
  }

  const hasActiveFilters = searchQuery.trim() !== '' || statusFilter !== 'all';

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-krait-border shrink-0 bg-background">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-medium flex items-center gap-2 text-text-primary">
            <Activity className="w-5 h-5 text-primary" /> Analysis
          </h1>
          <Link
            href={`/${workspaceSlug}/analysis/new`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md btn-shimmer text-primary-foreground text-[12px] font-semibold transition-all active:scale-[0.98]"
          >
            <Plus className="w-3.5 h-3.5" />
            New Analysis
          </Link>
        </div>

        {!isLoading && allJobs.length > 0 && (
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-krait-surface1 border border-krait-border rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <BarChart3 className="w-3.5 h-3.5 text-text-tertiary" />
                <p className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Total</p>
              </div>
              <p className="text-xl font-semibold text-text-primary tabular-nums">{stats.total}</p>
            </div>
            <div className="bg-krait-surface1 border border-krait-border rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                <p className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Completed</p>
              </div>
              <p className="text-xl font-semibold text-green-400 tabular-nums">{stats.completed}</p>
            </div>
            <div className="bg-krait-surface1 border border-krait-border rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <Loader2 className="w-3.5 h-3.5 text-yellow-400" />
                <p className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">In Progress</p>
              </div>
              <p className="text-xl font-semibold text-yellow-400 tabular-nums">{stats.inProgress}</p>
            </div>
            <div className="bg-krait-surface1 border border-krait-border rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <XCircle className="w-3.5 h-3.5 text-red-400" />
                <p className="text-[11px] text-text-tertiary uppercase tracking-wider font-medium">Failed</p>
              </div>
              <p className="text-xl font-semibold text-red-400 tabular-nums">{stats.failed}</p>
            </div>
          </div>
        )}

        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-[260px]">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); setPage(1); }}
              placeholder="Search by repo or branch..."
              className="w-full bg-krait-surface1 border border-krait-border text-[12px] text-text-primary rounded-md pl-8 pr-3 py-1.5 placeholder:text-text-tertiary focus:border-primary focus:outline-none transition-colors"
            />
          </div>
          <div className="flex items-center gap-1 bg-krait-surface1 border border-krait-border rounded-md p-0.5">
            {FILTER_TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => { setStatusFilter(tab.key); setPage(1); }}
                className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                  statusFilter === tab.key
                    ? 'bg-krait-surface3 text-text-primary'
                    : 'text-text-tertiary hover:text-text-secondary'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {hasActiveFilters && (
            <button
              onClick={() => { setSearchQuery(''); setStatusFilter('all'); }}
              className="flex items-center gap-1 text-[11px] text-text-tertiary hover:text-text-primary transition-colors"
            >
              <FilterX className="w-3 h-3" />
              Clear
            </button>
          )}
          {isLoading && <Loader2 className="w-4 h-4 text-venom-yellow animate-spin ml-auto shrink-0" />}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-background p-6">
        {isLoading && allJobs.length === 0 ? (
          <div className="space-y-4">
            {Array.from({ length: 2 }).map((_, i) => (
              <JobGroupSkeleton key={i} />
            ))}
          </div>
        ) : groupedJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Activity className="w-10 h-10 text-text-tertiary mb-3" />
            <p className="text-base font-medium text-text-primary mb-1">
              {hasActiveFilters ? 'No matching analyses' : 'No analyses yet'}
            </p>
            <p className="text-sm text-text-tertiary mb-4 max-w-sm">
              {hasActiveFilters
                ? 'Try adjusting your search or filter.'
                : 'Run your first analysis to check repository health, find issues, and get performance insights.'}
            </p>
            {!hasActiveFilters && (
              <Link
                href={`/${workspaceSlug}/analysis/new`}
                className="flex items-center gap-2 px-4 py-2 rounded-md btn-shimmer text-primary-foreground text-[13px] font-semibold"
              >
                <Plus className="w-4 h-4" />
                Run First Analysis
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {groupedJobs.map(([repoKey, jobs]) => (
              <JobGroup key={repoKey} repoKey={repoKey} jobs={jobs} workspaceSlug={workspaceSlug} />
            ))}

            {total > 50 && (
              <div className="flex items-center justify-between pt-2">
                <span className="text-[12px] text-text-tertiary">
                  Showing {groupedJobs.length} group{groupedJobs.length !== 1 && 's'}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page <= 1}
                    className="px-3 py-1.5 text-[12px] font-medium border border-krait-border rounded-md bg-krait-surface1 text-text-secondary disabled:opacity-30 hover:bg-krait-surface2 transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(Math.min(Math.ceil(total / 50), page + 1))}
                    disabled={page >= Math.ceil(total / 50)}
                    className="px-3 py-1.5 text-[12px] font-medium border border-krait-border rounded-md bg-krait-surface1 text-text-secondary disabled:opacity-30 hover:bg-krait-surface2 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
