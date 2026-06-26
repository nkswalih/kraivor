'use client';

import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Bug,
  AlertTriangle,
  Zap,
  FileText,
  Activity,
  Clock,
  Files,
  List,
} from 'lucide-react';
import Link from 'next/link';
import { formatRelativeTime } from '@/lib/utils';
import { useJob, useReport, useFindingsSummary } from '@/lib/hooks/use-analysis';
import { JobStatusBadge } from '@/components/analysis/job-status-badge';
import { ProgressBar } from '@/components/analysis/progress-bar';
import { ScoreGauge } from '@/components/analysis/score-gauge';
function ScoreCard({
  label,
  score,
}: {
  label: string;
  score: number | null | undefined;
}) {
  if (score == null) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-3 flex flex-col items-center gap-1">
      <ScoreGauge score={score} size={80} strokeWidth={6} />
      <span className="text-[11px] text-text-tertiary uppercase tracking-wider mt-1">{label}</span>
    </div>
  );
}

export default function JobDetailPage() {
  const params = useParams<{ workspace: string; jobId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';

  const { data: job, isLoading, error } = useJob(jobId);
  const { data: report } = useReport(jobId);
  const { data: summary } = useFindingsSummary(jobId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 text-venom-yellow animate-spin" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <AlertCircle className="w-10 h-10 text-color-error mb-3" />
        <p className="text-base font-medium text-text-primary mb-1">Job not found</p>
        <p className="text-sm text-text-tertiary">{error?.message || 'Unable to load analysis job'}</p>
        <Link
          href={`/${workspaceSlug}/analysis`}
          className="mt-4 px-4 py-2 rounded-md border border-border bg-card text-[13px] text-foreground hover:bg-white/5 transition-colors"
        >
          Back to Analysis
        </Link>
      </div>
    );
  }

  const isRunning = !['completed', 'failed'].includes(job.status);
  const isComplete = job.status === 'completed';

  return (
    <div className="flex flex-col h-full animate-fade-up">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center gap-3 mb-2">
          <Link
            href={`/${workspaceSlug}/analysis`}
            className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary" />
            Analysis {job.job_id.slice(0, 8)}
          </h1>
          <JobStatusBadge status={job.status} />
        </div>
        <div className="flex items-center gap-4 text-[12px] text-text-tertiary">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Started {formatRelativeTime(job.created_at)}
          </span>
          {job.repo_url && <span>Repo: {job.repo_url.replace('https://github.com/', '')}</span>}
          <span>Branch: {job.branch}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isRunning && (
          <div className="max-w-2xl mx-auto space-y-6">
            <ProgressBar pct={job.progress_pct} message={job.progress_message} className="mb-4" />
            <div className="flex items-center gap-2 text-text-tertiary text-[12px]">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-venom-yellow" />
              Analysis in progress — this page updates automatically
            </div>
          </div>
        )}

        {job.status === 'failed' && (
          <div className="max-w-2xl mx-auto p-4 border border-red-500/30 bg-red-500/10 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-[13px] font-medium text-red-400">Analysis Failed</p>
              <p className="text-[12px] text-text-tertiary mt-1">{job.error_message || 'Unknown error'}</p>
            </div>
          </div>
        )}

        {isComplete && (
          <div className="space-y-8 max-w-4xl">
            {/* Overall Score */}
            <div className="flex flex-col items-center">
              <ScoreGauge
                score={report?.overall_score ?? job.overall_score ?? 0}
                size={160}
                strokeWidth={12}
              />
            </div>

            {/* Category Scores */}
            {report && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <ScoreCard label="Performance" score={report.performance_score} />
                <ScoreCard label="Security" score={report.security_score} />
                <ScoreCard label="Reliability" score={report.reliability_score} />
                <ScoreCard label="Maintainability" score={report.maintainability_score} />
                <ScoreCard label="DevOps" score={report.devops_score} />
              </div>
            )}

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {report && (
                <>
                  <div className="bg-card border border-border rounded-lg p-4 text-center">
                    <Files className="w-5 h-5 text-blue-400 mx-auto mb-1" />
                    <p className="text-2xl font-semibold text-foreground">{report.total_files}</p>
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Files</p>
                  </div>
                  <div className="bg-card border border-border rounded-lg p-4 text-center">
                    <List className="w-5 h-5 text-yellow-400 mx-auto mb-1" />
                    <p className="text-2xl font-semibold text-foreground">{report.total_findings}</p>
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Findings</p>
                  </div>
                  <div className="bg-card border border-border rounded-lg p-4 text-center">
                    <Clock className="w-5 h-5 text-green-400 mx-auto mb-1" />
                    <p className="text-2xl font-semibold text-foreground">
                      {report.duration_seconds ? `${report.duration_seconds}s` : '—'}
                    </p>
                    <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Duration</p>
                  </div>
                </>
              )}
            </div>

            {/* Findings Summary */}
            {summary && (
              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-[13px] font-medium text-foreground mb-3">Findings by Severity</h3>
                <div className="flex gap-1 h-4 rounded-full overflow-hidden">
                  {summary.by_severity.critical > 0 && (
                    <div
                      className="bg-red-500 h-full transition-all"
                      style={{ width: `${(summary.by_severity.critical / summary.total) * 100}%` }}
                      title={`Critical: ${summary.by_severity.critical}`}
                    />
                  )}
                  {summary.by_severity.high > 0 && (
                    <div
                      className="bg-orange-500 h-full transition-all"
                      style={{ width: `${(summary.by_severity.high / summary.total) * 100}%` }}
                      title={`High: ${summary.by_severity.high}`}
                    />
                  )}
                  {summary.by_severity.medium > 0 && (
                    <div
                      className="bg-yellow-500 h-full transition-all"
                      style={{ width: `${(summary.by_severity.medium / summary.total) * 100}%` }}
                      title={`Medium: ${summary.by_severity.medium}`}
                    />
                  )}
                  {summary.by_severity.low > 0 && (
                    <div
                      className="bg-blue-500 h-full transition-all"
                      style={{ width: `${(summary.by_severity.low / summary.total) * 100}%` }}
                      title={`Low: ${summary.by_severity.low}`}
                    />
                  )}
                </div>
                <div className="flex gap-4 mt-2 text-[11px] text-text-tertiary">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Critical {summary.by_severity.critical}</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" /> High {summary.by_severity.high}</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Medium {summary.by_severity.medium}</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Low {summary.by_severity.low}</span>
                </div>
              </div>
            )}

            {/* Navigation Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <Link
                href={`/${workspaceSlug}/analysis/jobs/${jobId}/findings`}
                className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
              >
                <Activity className="w-5 h-5 text-yellow-400 mb-2" />
                <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Findings</p>
                <p className="text-[11px] text-text-tertiary mt-1">Browse all detected issues</p>
              </Link>
              <Link
                href={`/${workspaceSlug}/analysis/jobs/${jobId}/dead-code`}
                className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
              >
                <Bug className="w-5 h-5 text-orange-400 mb-2" />
                <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Dead Code</p>
                <p className="text-[11px] text-text-tertiary mt-1">Unused imports, functions, and more</p>
              </Link>
              <Link
                href={`/${workspaceSlug}/analysis/jobs/${jobId}/errors`}
                className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
              >
                <AlertTriangle className="w-5 h-5 text-red-400 mb-2" />
                <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Error Patterns</p>
                <p className="text-[11px] text-text-tertiary mt-1">Bare excepts, missing timeouts, etc.</p>
              </Link>
              <Link
                href={`/${workspaceSlug}/analysis/jobs/${jobId}/performance`}
                className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
              >
                <Zap className="w-5 h-5 text-yellow-400 mb-2" />
                <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Performance</p>
                <p className="text-[11px] text-text-tertiary mt-1">RPM estimates, latency, bottlenecks</p>
              </Link>
              <Link
                href={`/${workspaceSlug}/analysis/jobs/${jobId}/guide`}
                className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
              >
                <FileText className="w-5 h-5 text-blue-400 mb-2" />
                <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Enterprise Guide</p>
                <p className="text-[11px] text-text-tertiary mt-1">Remediation plan and migration path</p>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
