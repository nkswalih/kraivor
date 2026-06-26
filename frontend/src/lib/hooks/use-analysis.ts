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

export function useJobsList(page = 1, pageSize = 20) {
  return useQuery<JobListResponse>({
    queryKey: ['analysis-jobs', page, pageSize],
    queryFn: () => analysisService.jobs.list(page, pageSize),
    refetchInterval: 5000,
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
  filters?: { severity?: string; category?: string; page?: number; pageSize?: number }
) {
  return useQuery({
    queryKey: ['analysis-findings', jobId, filters],
    queryFn: () =>
      analysisService.findings.list({
        jobId: jobId!,
        severity: filters?.severity,
        category: filters?.category,
        page: filters?.page,
        pageSize: filters?.pageSize,
      }),
    enabled: !!jobId,
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
  return useQuery<EnterpriseGuide>({
    queryKey: ['analysis-guide', jobId],
    queryFn: () => analysisService.enterpriseGuide.get(jobId!),
    enabled: !!jobId,
  });
}
