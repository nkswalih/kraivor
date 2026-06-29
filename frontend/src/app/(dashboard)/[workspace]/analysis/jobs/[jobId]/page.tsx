'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
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
  RotateCcw,
  Trash2,
  PanelRightOpen,
} from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { formatRelativeTime } from '@/lib/utils';
import {
  useJob,
  useReport,
  useFindingsSummary,
  useCategoryCounts,
  useScoreHistory,
  useDeleteJob,
  useStartAnalysis,
  useFindings,
} from '@/lib/hooks/use-analysis';
import { JobStatusBadge } from '@/components/analysis/job-status-badge';
import { ProgressBar } from '@/components/analysis/progress-bar';
import { ScoreGauge } from '@/components/analysis/score-gauge';
import { EngineStatusCard } from '@/components/analysis/engine-status-card';
import { BlockedOverall } from '@/components/analysis/blocked-overall';
import { ScoreHistoryChart } from '@/components/analysis/score-history-chart';
import { AnalysisInsightsSidebar } from '@/components/analysis/sidebar/AnalysisInsightsSidebar';

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
  const router = useRouter();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';
  const [reanalyzing, setReanalyzing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const { data: job, isLoading, error } = useJob(jobId);
  const { data: report } = useReport(jobId);
  const { data: summary } = useFindingsSummary(jobId);
  const { data: findingsData } = useFindings(jobId);
  const { data: counts } = useCategoryCounts(jobId);
  const { data: scoreHistory, isLoading: isScoreHistoryLoading, error: scoreHistoryError } = useScoreHistory(
    job?.repo_id ?? null,
  );
  const startAnalysis = useStartAnalysis();
  const deleteJob = useDeleteJob();
  const queryClient = useQueryClient();
  const prevStatusRef = useRef<string | undefined>(undefined);

  const handleReanalyze = async () => {
    if (!job || reanalyzing) return;
    setReanalyzing(true);
    try {
      const newJob = await startAnalysis.mutateAsync({
        repo_id: job.repo_id,
        workspace_id: job.workspace_id,
        repo_url: job.repo_url,
        branch: job.branch,
      });
      toast.success('Reanalysis started');
      router.push(`/${workspaceSlug}/analysis/jobs/${newJob.job_id}`);
    } catch {
      toast.error('Failed to start reanalysis');
    } finally {
      setReanalyzing(false);
    }
  };

  const handleDelete = async () => {
    if (!job || deleting) return;
    setDeleting(true);
    setShowDeleteConfirm(false);
    try {
      await deleteJob.mutateAsync(jobId);
      toast.success('Analysis deleted');
      router.push(`/${workspaceSlug}/analysis`);
    } catch {
      toast.error('Failed to delete analysis');
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    const currentStatus = job?.status;
    const prevStatus = prevStatusRef.current;
    prevStatusRef.current = currentStatus;

    if (currentStatus === 'completed' && prevStatus !== 'completed') {
      queryClient.invalidateQueries({ queryKey: ['analysis-report', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-findings-summary', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-findings', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-dead-code', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-error-findings', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-perf-metrics', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-simulation', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-guide', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-score-history', job?.repo_id] });
    }
  }, [job?.status, jobId, job?.repo_id, queryClient]);

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
  const engineKeys = ['security', 'reliability', 'maintainability', 'devops', 'performance'];

  const sidebarLoading = isLoading || !job;

  return (
    <div className="flex h-full animate-fade-up">
      {/* Main content column */}
      <div className="flex-1 flex flex-col min-w-0">
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
            <div className="ml-auto flex items-center gap-2">
              {/* Mobile sidebar toggle */}
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-1.5 rounded-md border border-border bg-card text-muted-foreground hover:text-foreground transition-colors"
                title="Open insights"
              >
                <PanelRightOpen className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleting}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-red-500/30 bg-red-500/10 text-[12px] text-red-400 hover:bg-red-500/20 hover:border-red-500/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Permanently delete this analysis"
              >
                <Trash2 className="w-3.5 h-3.5" />
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
              <button
                onClick={handleReanalyze}
                disabled={reanalyzing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border bg-card text-[12px] text-text-secondary hover:text-foreground hover:border-venom-yellow/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Run analysis again on this repository"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${reanalyzing ? 'animate-spin' : ''}`} />
                {reanalyzing ? 'Reanalyzing...' : 'Reanalyze'}
              </button>
            </div>
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
              <div className="space-y-3">
                <h3 className="text-[12px] font-medium text-text-tertiary uppercase tracking-wider">Engine Status</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {engineKeys.map(k => (
                    <EngineStatusCard
                      key={k}
                      engine={k}
                      status={job.engine_statuses[k]}
                      score={report?.[k === 'performance' ? 'performance_score' : `${k}_score` as keyof typeof report] as number | null | undefined}
                    />
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2 text-text-tertiary text-[12px]">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-venom-yellow" />
                Analysis in progress — this page updates automatically
              </div>
            </div>
          )}

          {job.status === 'failed' && (
            <div className="max-w-2xl mx-auto space-y-4">
              <div className="p-4 border border-red-500/30 bg-red-500/10 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-[13px] font-medium text-red-400">Analysis Failed</p>
                  <p className="text-[12px] text-text-tertiary mt-1">{job.error_message || 'Unknown error'}</p>
                </div>
              </div>
              {job.blocked_by.length > 0 && (
                <BlockedOverall blockedBy={job.blocked_by} />
              )}
              <div className="space-y-3">
                <h3 className="text-[12px] font-medium text-text-tertiary uppercase tracking-wider">Engine Status</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {engineKeys.map(k => (
                    <EngineStatusCard
                      key={k}
                      engine={k}
                      status={job.engine_statuses[k]}
                      score={undefined}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {isComplete && (
            <div className="space-y-8 max-w-4xl">
              {/* Blocked Overall Banner */}
              {job.blocked_by.length > 0 && (
                <BlockedOverall blockedBy={job.blocked_by} />
              )}

              {/* Overall Score */}
              <div className="flex flex-col items-center">
                <ScoreGauge
                  score={report?.overall_score ?? job.overall_score ?? 0}
                  size={160}
                  strokeWidth={12}
                />
              </div>

              {/* Engine Status Cards */}
              <div className="space-y-3">
                <h3 className="text-[12px] font-medium text-text-tertiary uppercase tracking-wider">Engine Status</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
                  {engineKeys.map(k => {
                    const scoreKey = k === 'performance' ? 'performance_score' : `${k}_score` as keyof typeof report;
                    const engineScore = report?.[scoreKey] as number | null | undefined;
                    return (
                      <EngineStatusCard
                        key={k}
                        engine={k}
                        status={job.engine_statuses[k]}
                        score={engineScore}
                      />
                    );
                  })}
                </div>
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
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
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
                        {report.duration_seconds ? `${report.duration_seconds}s` : '\u2014'}
                      </p>
                      <p className="text-[11px] text-text-tertiary uppercase tracking-wider">Duration</p>
                    </div>
                  </>
                )}
              </div>

              {/* Score History Chart */}
              <ScoreHistoryChart
                entries={scoreHistory?.entries ?? []}
                isLoading={isScoreHistoryLoading}
                error={scoreHistoryError as Error | null}
              />

              {/* Findings Summary */}
              {summary && (
                <div className="bg-card border border-border rounded-lg p-4">
                  <h3 className="text-[13px] font-medium text-foreground mb-3">Findings Summary</h3>
                  {summary.total > 0 && (
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4 text-[12px]">
                      {Object.entries(summary.by_category).map(([cat, cnt]) =>
                        cnt > 0 ? (
                          <div key={cat} className="bg-background rounded px-2 py-1 flex justify-between">
                            <span className="text-text-tertiary capitalize">{cat}</span>
                            <span className="text-foreground font-medium">{cnt}</span>
                          </div>
                        ) : null
                      )}
                    </div>
                  )}
                  <h4 className="text-[12px] font-medium text-text-tertiary mb-2">by Severity</h4>
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
                  <p className="text-[11px] text-text-tertiary mt-1">{counts?.findings ?? 0} issue{counts?.findings !== 1 ? 's' : ''} detected</p>
                </Link>
                <Link
                  href={`/${workspaceSlug}/analysis/jobs/${jobId}/dead-code`}
                  className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
                >
                  <Bug className="w-5 h-5 text-orange-400 mb-2" />
                  <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Dead Code</p>
                  <p className="text-[11px] text-text-tertiary mt-1">{counts?.deadCode ?? 0} dead code entr{counts?.deadCode === 1 ? 'y' : 'ies'}</p>
                </Link>
                <Link
                  href={`/${workspaceSlug}/analysis/jobs/${jobId}/errors`}
                  className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
                >
                  <AlertTriangle className="w-5 h-5 text-red-400 mb-2" />
                  <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Error Patterns</p>
                  <p className="text-[11px] text-text-tertiary mt-1">{counts?.errors ?? 0} error pattern{counts?.errors !== 1 ? 's' : ''}</p>
                </Link>
                <Link
                  href={`/${workspaceSlug}/analysis/jobs/${jobId}/performance`}
                  className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
                >
                  <Zap className="w-5 h-5 text-yellow-400 mb-2" />
                  <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Performance</p>
                  <p className="text-[11px] text-text-tertiary mt-1">{counts?.perf ?? 0} metric{(counts?.perf ?? 0) !== 1 ? 's' : ''}</p>
                </Link>
                <Link
                  href={`/${workspaceSlug}/analysis/jobs/${jobId}/guide`}
                  className="p-4 rounded-lg border border-border bg-card hover:border-venom-yellow/30 hover:shadow-venom transition-all group"
                >
                  <FileText className="w-5 h-5 text-blue-400 mb-2" />
                  <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors">Enterprise Guide</p>
                  <p className="text-[11px] text-text-tertiary mt-1">{counts?.hasGuide ? 'Available' : 'Not generated'}</p>
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:block">
        <AnalysisInsightsSidebar
          job={job}
          report={report}
          findingsSummary={summary}
          findings={findingsData?.findings ?? null}
          isLoading={sidebarLoading}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Mobile/tablet sidebar drawer overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="absolute right-0 top-0 h-full w-[85vw] max-w-[380px] animate-in-up">
            <AnalysisInsightsSidebar
              job={job}
              report={report}
              findingsSummary={summary}
              findings={findingsData?.findings ?? null}
              isLoading={sidebarLoading}
              onClose={() => setSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-base font-semibold text-foreground mb-2">Delete Analysis</h3>
            <p className="text-[13px] text-text-secondary mb-1">
              This will permanently delete all findings, scores, reports, and stored files for this analysis.
            </p>
            <p className="text-[13px] text-red-400 font-medium mb-4">
              This action cannot be undone.
            </p>
            <div className="flex items-center gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 rounded-md border border-border bg-card text-[13px] text-text-secondary hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 rounded-md bg-red-600 text-white text-[13px] font-medium hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleting ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
