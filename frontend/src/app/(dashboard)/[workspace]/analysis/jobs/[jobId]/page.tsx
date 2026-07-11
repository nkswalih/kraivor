'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import dynamic from 'next/dynamic';
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
  RotateCcw,
  Trash2,
  PanelRightOpen,
  BarChart3,
  Star,
} from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { formatRelativeTime } from '@/lib/utils';
import {
  useJob,
  useReport,
  useFindingsSummary,
  useJobStatistics,
  useScoreHistory,
  useDeleteJob,
  useStartAnalysis,
  useFindings,
} from '@/lib/hooks/use-analysis';
import { useDetailBreadcrumb } from '@/lib/hooks/use-detail-breadcrumb';
import { JobStatusBadge } from '@/components/analysis/job-status-badge';
import { ProgressBar } from '@/components/analysis/progress-bar';
import { BlockedOverall } from '@/components/analysis/blocked-overall';
import { HeroCard } from '@/components/analysis/hero-card';
import { EngineCard } from '@/components/analysis/engine-card';
import { MetricCard, MetricCardSkeleton } from '@/components/analysis/metric-card';
import { ChartCard } from '@/components/analysis/chart-card';
import { AnalysisModuleCard, AnalysisModuleCardSkeleton } from '@/components/analysis/analysis-module-card';

const AnalysisTrendChart = dynamic(
  () => import('@/components/analysis/analysis-trend-chart').then(m => ({ default: m.AnalysisTrendChart })),
  { ssr: false },
);
const SeverityDonutChart = dynamic(
  () => import('@/components/analysis/severity-donut-chart').then(m => ({ default: m.SeverityDonutChart })),
  { ssr: false },
);
const AnalysisInsightsSidebar = dynamic(
  () => import('@/components/analysis/sidebar/AnalysisInsightsSidebar').then(m => ({ default: m.AnalysisInsightsSidebar })),
  { ssr: false },
);

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
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('all');

  const { data: job, isLoading, error } = useJob(jobId);
  useDetailBreadcrumb(job ? `Analysis ${job.job_id.slice(0, 8)}` : null);
  const { data: report } = useReport(jobId);
  const { data: summary, isLoading: isSummaryLoading, error: summaryError } = useFindingsSummary(jobId);
  const { data: findingsData } = useFindings(jobId);
  const { data: stats, isLoading: isCountsLoading } = useJobStatistics(jobId);
  const { data: scoreHistory, isLoading: isScoreHistoryLoading, error: scoreHistoryError } = useScoreHistory(
    job?.repo_id ?? null,
  );
  const startAnalysis = useStartAnalysis();
  const deleteJob = useDeleteJob();
  const queryClient = useQueryClient();
  const prevStatusRef = useRef<string | undefined>(undefined);

  const filteredEntries = useMemo(() => {
    if (timeRange === 'all' || !scoreHistory?.entries) return scoreHistory?.entries ?? [];
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - (timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90));
    return scoreHistory.entries.filter(e => new Date(e.time) >= cutoff);
  }, [timeRange, scoreHistory?.entries]);

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
      queryClient.invalidateQueries({ queryKey: ['analysis-job-statistics', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-guide', jobId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-metadata', jobId] });
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
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {engineKeys.map(k => (
                    <EngineCard
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
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {engineKeys.map(k => (
                    <EngineCard
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
            <div className="space-y-8 max-w-5xl mx-auto">
              {/* Blocked Overall Banner */}
              {job.blocked_by.length > 0 && (
                <BlockedOverall blockedBy={job.blocked_by} />
              )}

              {/* Hero Card */}
              <HeroCard
                overallScore={report?.overall_score ?? job.overall_score ?? 0}
                report={report}
                scoreHistory={scoreHistory?.entries}
                job={job}
              />

              {/* Engine Status Cards */}
              <div className="space-y-3">
                <h3 className="text-[12px] font-medium text-text-tertiary uppercase tracking-wider">Engine Status</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                  {engineKeys.map(k => {
                    const scoreKey = k === 'performance' ? 'performance_score' : `${k}_score` as keyof typeof report;
                    const engineScore = report?.[scoreKey] as number | null | undefined;
                    return (
                      <EngineCard
                        key={k}
                        engine={k}
                        status={job.engine_statuses[k]}
                        score={engineScore}
                      />
                    );
                  })}
                </div>
              </div>

              {/* Section 3: Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ChartCard title="Score Trend" icon={BarChart3}>
                  <AnalysisTrendChart
                    entries={filteredEntries}
                    isLoading={isScoreHistoryLoading}
                    error={scoreHistoryError as Error | null}
                    timeRange={timeRange}
                    onTimeRangeChange={setTimeRange}
                  />
                </ChartCard>

                <ChartCard title="Findings by Severity" icon={AlertCircle}>
                  <SeverityDonutChart
                    summary={summary}
                    isLoading={isSummaryLoading}
                    error={summaryError as Error | null}
                  />
                </ChartCard>
              </div>

              {/* Section 4: Repository Summary */}
              <div>
                <h3 className="text-[12px] font-medium text-text-tertiary uppercase tracking-wider mb-4">
                  Repository Summary
                </h3>
                {isCountsLoading ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {[1,2,3,4,5,6].map(i => <MetricCardSkeleton key={i} />)}
                  </div>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <MetricCard
                      icon={Activity}
                      value={stats?.findings_count ?? 0}
                      title="Findings"
                      subtitle="Issues detected in codebase"
                      status={(stats?.findings_count ?? 0) > 0 ? 'attention' : 'healthy'}
                      color="green"
                      index={0}
                      onClick={() => router.push(`/${workspaceSlug}/analysis/jobs/${jobId}/findings`)}
                    />
                    <MetricCard
                      icon={Bug}
                      value={stats?.dead_code_count ?? 0}
                      title="Dead Code"
                      subtitle="Unused files, methods, imports"
                      status={(stats?.dead_code_count ?? 0) > 0 ? 'attention' : 'healthy'}
                      color="orange"
                      index={1}
                      onClick={() => router.push(`/${workspaceSlug}/analysis/jobs/${jobId}/dead-code`)}
                    />
                    <MetricCard
                      icon={AlertTriangle}
                      value={stats?.error_findings_count ?? 0}
                      title="Error Patterns"
                      subtitle="Exception & reliability issues"
                      status={(stats?.error_findings_count ?? 0) > 0 ? 'attention' : 'healthy'}
                      color="red"
                      index={2}
                      onClick={() => router.push(`/${workspaceSlug}/analysis/jobs/${jobId}/errors`)}
                    />
                    <MetricCard
                      icon={Zap}
                      value={stats?.performance_metrics_count ?? 0}
                      title="Performance"
                      subtitle="Bottlenecks & latency metrics"
                      status={(stats?.performance_metrics_count ?? 0) > 0 ? 'attention' : 'healthy'}
                      color="blue"
                      index={3}
                      onClick={() => router.push(`/${workspaceSlug}/analysis/jobs/${jobId}/performance`)}
                    />
                    <MetricCard
                      icon={Star}
                      value={stats?.counts_by_category?.quality ?? 0}
                      title="Code Churn"
                      subtitle="Hotspot files from commit history"
                      status={(stats?.counts_by_category?.quality ?? 0) > 0 ? 'attention' : 'healthy'}
                      color="pink"
                      index={4}
                      onClick={() => router.push(`/${workspaceSlug}/analysis/jobs/${jobId}/findings?category=quality`)}
                    />
                    <MetricCard
                      icon={FileText}
                      value={stats?.enterprise_guide_exists ? 'Ready' : '—'}
                      title="Enterprise Guide"
                      subtitle="AI-assisted analysis summary"
                      status={stats?.enterprise_guide_exists ? 'available' : 'pending'}
                      color="purple"
                      index={5}
                      onClick={() => router.push(`/${workspaceSlug}/analysis/jobs/${jobId}/guide`)}
                    />
                  </div>
                )}
              </div>

              {/* Section 5: Analysis Workspaces */}
              <div>
                <h3 className="text-[12px] font-medium text-text-tertiary uppercase tracking-wider mb-4">
                  Analysis Workspaces
                </h3>
                {isCountsLoading ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    {[1,2,3,4,5].map(i => <AnalysisModuleCardSkeleton key={i} />)}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <AnalysisModuleCard
                      href={`/${workspaceSlug}/analysis/jobs/${jobId}/findings`}
                      icon={Activity}
                      title="Findings"
                      count={(stats?.findings_count ?? 0) + ((stats?.findings_count ?? 0) !== 1 ? ' Findings' : ' Finding')}
                      description="Browse every issue detected during analysis. Review severity, category, and file-level details."
                      stats={summary ? [
                        { label: 'Critical', value: summary.by_severity.critical ?? 0, color: '#ef4444' },
                        { label: 'High', value: summary.by_severity.high ?? 0, color: '#f97316' },
                        { label: 'Low', value: summary.by_severity.low ?? 0, color: '#3b82f6' },
                      ] : undefined}
                      color="green"
                      actionLabel="Open Findings"
                      index={0}
                    />
                    <AnalysisModuleCard
                      href={`/${workspaceSlug}/analysis/jobs/${jobId}/dead-code`}
                      icon={Bug}
                      title="Dead Code"
                      count={(stats?.dead_code_count ?? 0) + ((stats?.dead_code_count ?? 0) !== 1 ? ' Entries' : ' Entry')}
                      description="Unused files, methods, and imports in your codebase. Clean up to reduce maintenance burden."
                      color="orange"
                      actionLabel="Open Dead Code"
                      index={1}
                    />
                    <AnalysisModuleCard
                      href={`/${workspaceSlug}/analysis/jobs/${jobId}/errors`}
                      icon={AlertTriangle}
                      title="Error Patterns"
                      count={(stats?.error_findings_count ?? 0) + ((stats?.error_findings_count ?? 0) !== 1 ? ' Patterns' : ' Pattern')}
                      description="Unhandled exceptions, retry loops, and silent failures. Fix reliability issues before they reach production."
                      color="red"
                      actionLabel="Open Error Analysis"
                      index={2}
                    />
                    <AnalysisModuleCard
                      href={`/${workspaceSlug}/analysis/jobs/${jobId}/performance`}
                      icon={Zap}
                      title="Performance"
                      count={(stats?.performance_metrics_count ?? 0) + ((stats?.performance_metrics_count ?? 0) !== 1 ? ' Metrics' : ' Metric')}
                      description="Endpoint analysis, simulation results, and latency metrics. Optimize slow paths and reduce response times."
                      stats={report ? [
                        { label: 'Score', value: report.performance_score ?? '—', color: '#3b82f6' },
                      ] : undefined}
                      color="blue"
                      actionLabel="Open Performance"
                      index={3}
                    />
                    <AnalysisModuleCard
                      href={`/${workspaceSlug}/analysis/jobs/${jobId}/findings?category=quality`}
                      icon={Star}
                      title="Code Churn"
                      count={(stats?.counts_by_category?.quality ?? 0) + ((stats?.counts_by_category?.quality ?? 0) !== 1 ? ' Issues' : ' Issue')}
                      description="Files with high change frequency and spread ownership. Review churn hotspots for refactoring opportunities."
                      color="pink"
                      actionLabel="Open Churn Analysis"
                      index={4}
                    />
                    <AnalysisModuleCard
                      href={`/${workspaceSlug}/analysis/jobs/${jobId}/guide`}
                      icon={FileText}
                      title="Enterprise Guide"
                      count={stats?.enterprise_guide_exists ? 'AI Generated' : 'Not Generated'}
                      description="Architecture review, security checklist, and deployment guidance tailored to your codebase."
                      color="purple"
                      actionLabel="Open Guide"
                      index={5}
                    />
                  </div>
                )}
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
