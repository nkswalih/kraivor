'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analysisService } from '@/lib/api/analysis-service';
import type {
  AnalysisJob,
  JobListResponse,
  StartAnalysisRequest,
  FindingsSummary,
  Report,
  DeadCodeListResponse,
  ErrorFindingListResponse,
  PerformanceMetricListResponse,
  SimulationResultListResponse,
  ScoreHistoryListResponse,
  EnterpriseGuide,
} from '@/types/domain/analysis';

// ─── Job Polling ────────────────────────────────────────

const terminalStatuses = new Set(['completed', 'failed']);

export function useJob(jobId: string | null) {
  return useQuery<AnalysisJob>({
    queryKey: ['analysis-job', jobId],
    queryFn: () => analysisService.jobs.get(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      if (terminalStatuses.has(data.status)) return false;
      return 2000;
    },
  });
}

// ─── Job List ───────────────────────────────────────────

export function useJobsList(page = 1, pageSize = 20, workspaceId?: string) {
  return useQuery<JobListResponse>({
    queryKey: ['analysis-jobs', workspaceId, page, pageSize],
    queryFn: () => analysisService.jobs.list(page, pageSize, workspaceId),
    enabled: !!workspaceId,
    refetchInterval: 5000,
  });
}

// ─── File Upload ─────────────────────────────────────────

export function useFileUpload() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisJob, Error, { workspaceId: string; file: File }>({
    mutationFn: ({ workspaceId, file }) =>
      analysisService.files.upload(workspaceId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis-jobs'] });
    },
  });
}

// ─── Start Analysis ─────────────────────────────────────

export function useStartAnalysis() {
  const queryClient = useQueryClient();
  return useMutation<AnalysisJob, Error, StartAnalysisRequest>({
    mutationFn: (data) => analysisService.jobs.start(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis-jobs'] });
    },
  });
}

// ─── Findings ───────────────────────────────────────────

export function useFindings(
  jobId: string | null,
  filters?: { severity?: string; category?: string; includeDismissed?: boolean; page?: number; pageSize?: number }
) {
  return useQuery({
    queryKey: ['analysis-findings', jobId, filters],
    queryFn: () =>
      analysisService.findings.list({
        jobId: jobId!,
        severity: filters?.severity,
        category: filters?.category,
        includeDismissed: filters?.includeDismissed,
        page: filters?.page,
        pageSize: filters?.pageSize,
      }),
    enabled: !!jobId,
  });
}

export function useDismissFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (findingIds: string[]) =>
      analysisService.findings.dismiss(findingIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis-findings'] });
    },
  });
}

export function useFindingsSummary(jobId: string | null) {
  return useQuery<FindingsSummary>({
    queryKey: ['analysis-findings-summary', jobId],
    queryFn: () => analysisService.findings.summary(jobId!),
    enabled: !!jobId,
  });
}

// ─── Report ─────────────────────────────────────────────

export function useReport(jobId: string | null) {
  return useQuery<Report>({
    queryKey: ['analysis-report', jobId],
    queryFn: () => analysisService.reports.byJob(jobId!),
    enabled: !!jobId,
  });
}

// ─── Dead Code ──────────────────────────────────────────

export function useDeadCode(jobId: string | null) {
  return useQuery<DeadCodeListResponse>({
    queryKey: ['analysis-dead-code', jobId],
    queryFn: () => analysisService.deadCode.list(jobId!),
    enabled: !!jobId,
  });
}

// ─── Error Findings ─────────────────────────────────────

export function useErrorFindings(jobId: string | null) {
  return useQuery<ErrorFindingListResponse>({
    queryKey: ['analysis-error-findings', jobId],
    queryFn: () => analysisService.errorFindings.list(jobId!),
    enabled: !!jobId,
  });
}

// ─── Performance Metrics ────────────────────────────────

export function usePerfMetrics(jobId: string | null) {
  return useQuery<PerformanceMetricListResponse>({
    queryKey: ['analysis-perf-metrics', jobId],
    queryFn: () => analysisService.perfMetrics.list(jobId!),
    enabled: !!jobId,
  });
}

// ─── Simulation Results ─────────────────────────────────

export function useSimulationResults(jobId: string | null) {
  return useQuery<SimulationResultListResponse>({
    queryKey: ['analysis-simulation', jobId],
    queryFn: () => analysisService.simulation.list(jobId!),
    enabled: !!jobId,
  });
}

// ─── Enterprise Guide ───────────────────────────────────

export function useEnterpriseGuide(jobId: string | null) {
  return useQuery<EnterpriseGuide | null>({
    queryKey: ['analysis-guide', jobId],
    queryFn: () => analysisService.enterpriseGuide.get(jobId!),
    enabled: !!jobId,
    retry: false,
  });
}

// ─── Score History ─────────────────────────────────────

export function useScoreHistory(repoId: string | null, limit = 50) {
  return useQuery<ScoreHistoryListResponse>({
    queryKey: ['analysis-score-history', repoId, limit],
    queryFn: () => analysisService.scoreHistory.list(repoId!, limit),
    enabled: !!repoId,
  });
}

// ─── Category Counts (for nav cards) ───────────────────

export interface CategoryCounts {
  findings: number;
  deadCode: number;
  errors: number;
  perf: number;
  simulation: number;
  hasGuide: boolean;
}

export function useCategoryCounts(jobId: string | null) {
  const find = useFindings(jobId, { pageSize: 1 });
  const dc = useDeadCode(jobId);
  const err = useErrorFindings(jobId);
  const perf = usePerfMetrics(jobId);
  const sim = useSimulationResults(jobId);
  const guide = useEnterpriseGuide(jobId);

  return {
    data: {
      findings: find.data?.total ?? 0,
      deadCode: dc.data?.total ?? 0,
      errors: err.data?.total ?? 0,
      perf: perf.data?.total ?? 0,
      simulation: sim.data?.total ?? 0,
      hasGuide: guide.data?.id != null,
    } satisfies CategoryCounts,
    isLoading: find.isLoading || dc.isLoading || err.isLoading || perf.isLoading || sim.isLoading,
  };
}
