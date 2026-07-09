import { API_ENDPOINTS } from '@/constants';
import { useAuthStore } from '@/lib/stores/auth-store';
import type {
  AnalysisJob,
  AnalysisMetadataResponse,
  JobListResponse,
  JobStatistics,
  StartAnalysisRequest,
  FindingsListResponse,
  FindingsSummary,
  Report,
  DeadCodeListResponse,
  ErrorFindingListResponse,
  PerformanceMetricListResponse,
  SimulationResultListResponse,
  ScoreHistoryListResponse,
  EnterpriseGuide,
} from '@/types/domain/analysis';

const BASE = process.env.NEXT_PUBLIC_ANALYSIS_API_URL ?? 'http://localhost:8003';

function getJwt(): string | null {
  if (typeof window === 'undefined') return null;
  return useAuthStore.getState().accessToken;
}

class AnalysisApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'AnalysisApiError';
  }
}

async function analysisFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${BASE}${path}`;
  const token = getJwt();

  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers as Record<string, string>),
    },
  });

  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new AnalysisApiError(
      res.status,
      body.error ?? body.code ?? 'unknown_error',
      body.message ?? body.detail ?? 'Request failed',
    );
  }

  return body as T;
}

function analysisGet<T>(path: string): Promise<T> {
  return analysisFetch<T>(path, { method: 'GET' });
}

function analysisPost<T>(path: string, body: unknown): Promise<T> {
  return analysisFetch<T>(path, {
    method: 'POST',
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

function analysisDelete<T>(path: string): Promise<T> {
  return analysisFetch<T>(path, { method: 'DELETE' });
}

export const analysisService = {
  scoreHistory: {
    list(repoId: string, limit = 50): Promise<ScoreHistoryListResponse> {
      return analysisGet<ScoreHistoryListResponse>(
        `${API_ENDPOINTS.ANALYSIS.SCORE_HISTORY(repoId)}?limit=${limit}`
      );
    },
  },
  files: {
    upload(workspaceId: string, file: File): Promise<AnalysisJob> {
      const formData = new FormData();
      formData.append('workspace_id', workspaceId);
      formData.append('file', file);
      return analysisFetch<AnalysisJob>(API_ENDPOINTS.ANALYSIS.FILE_UPLOAD, {
        method: 'POST',
        body: formData,
        headers: {}, // let fetch set content-type for multipart
      });
    },
  },
  jobs: {
    start(data: StartAnalysisRequest): Promise<AnalysisJob> {
      return analysisPost<AnalysisJob>(API_ENDPOINTS.ANALYSIS.JOB_START, data);
    },
    get(jobId: string): Promise<AnalysisJob> {
      return analysisGet<AnalysisJob>(API_ENDPOINTS.ANALYSIS.JOB_GET(jobId));
    },
    list(page = 1, pageSize = 20, workspaceId?: string): Promise<JobListResponse> {
      const q = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (workspaceId) q.set('workspace_id', workspaceId);
      return analysisGet<JobListResponse>(
        `${API_ENDPOINTS.ANALYSIS.JOBS_LIST}?${q}`
      );
    },
    delete(jobId: string): Promise<void> {
      return analysisDelete<void>(API_ENDPOINTS.ANALYSIS.JOB_DELETE(jobId));
    },
    statistics(jobId: string): Promise<JobStatistics> {
      return analysisGet<JobStatistics>(
        API_ENDPOINTS.ANALYSIS.JOB_STATISTICS(jobId)
      );
    },
    branches(repoUrl: string): Promise<string[]> {
      return analysisGet<string[]>(
        `${API_ENDPOINTS.ANALYSIS.BRANCHES}?url=${encodeURIComponent(repoUrl)}`
      );
    },
  },
  findings: {
    list(params: {
      jobId: string;
      severity?: string;
      category?: string;
      includeDismissed?: boolean;
      page?: number;
      pageSize?: number;
    }): Promise<FindingsListResponse> {
      const q = new URLSearchParams({ job_id: params.jobId });
      if (params.severity) q.set('severity', params.severity);
      if (params.category) q.set('category', params.category);
      if (params.includeDismissed) q.set('include_dismissed', 'true');
      if (params.page) q.set('page', String(params.page));
      if (params.pageSize) q.set('page_size', String(params.pageSize));
      return analysisGet<FindingsListResponse>(
        `${API_ENDPOINTS.ANALYSIS.FINDINGS}?${q}`
      );
    },
    summary(jobId: string): Promise<FindingsSummary> {
      return analysisGet<FindingsSummary>(
        `${API_ENDPOINTS.ANALYSIS.FINDINGS_SUMMARY}?job_id=${jobId}`
      );
    },
    dismiss(
      findingIds: string[],
      dismissed = true,
    ): Promise<{ dismissed: number; status: string }> {
      return analysisPost(`${API_ENDPOINTS.ANALYSIS.FINDINGS_DISMISS}`, {
        finding_ids: findingIds,
        dismissed,
      });
    },
  },
  reports: {
    byJob(jobId: string): Promise<Report> {
      return analysisGet<Report>(API_ENDPOINTS.ANALYSIS.REPORT_BY_JOB(jobId));
    },
    metadata(jobId: string): Promise<AnalysisMetadataResponse> {
      return analysisGet<AnalysisMetadataResponse>(
        API_ENDPOINTS.ANALYSIS.REPORT_METADATA_BY_JOB(jobId),
      );
    },
  },
  deadCode: {
    list(jobId: string): Promise<DeadCodeListResponse> {
      return analysisGet<DeadCodeListResponse>(
        `${API_ENDPOINTS.ANALYSIS.DEAD_CODE}?job_id=${jobId}`
      );
    },
  },
  errorFindings: {
    list(jobId: string): Promise<ErrorFindingListResponse> {
      return analysisGet<ErrorFindingListResponse>(
        `${API_ENDPOINTS.ANALYSIS.ERROR_FINDINGS}?job_id=${jobId}`
      );
    },
  },
  perfMetrics: {
    list(jobId: string): Promise<PerformanceMetricListResponse> {
      return analysisGet<PerformanceMetricListResponse>(
        `${API_ENDPOINTS.ANALYSIS.PERF_METRICS}?job_id=${jobId}`
      );
    },
  },
  simulation: {
    list(jobId: string): Promise<SimulationResultListResponse> {
      return analysisGet<SimulationResultListResponse>(
        `${API_ENDPOINTS.ANALYSIS.SIMULATION_RESULTS}?job_id=${jobId}`
      );
    },
  },
  enterpriseGuide: {
    get(jobId: string): Promise<EnterpriseGuide | null> {
      return analysisGet<EnterpriseGuide | null>(
        `${API_ENDPOINTS.ANALYSIS.ENTERPRISE_GUIDE}?job_id=${jobId}`
      );
    },
  },
};
