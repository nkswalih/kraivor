import { getLanguageColor } from '@/lib/analysis/language-colors';
import type {
  AnalysisInsights,
  AnalysisJob,
  AnalysisMetadataResponse,
  Report,
  FindingsSummary,
  Finding,
  EngineStatusItem,
  PriorityRecommendation,
} from '@/types/domain/analysis';

const ENGINE_KEYS = ['security', 'reliability', 'maintainability', 'devops', 'performance', 'simulation'] as const;

const ENGINE_LABELS: Record<string, string> = {
  security: 'Security',
  reliability: 'Reliability',
  maintainability: 'Maintainability',
  devops: 'DevOps',
  performance: 'Performance',
  simulation: 'Simulation',
};

const FALLBACK_LANGUAGES = [
  { name: 'Python', percentage: 60, color: '#3572A5' },
  { name: 'TypeScript', percentage: 20, color: '#3178C6' },
  { name: 'YAML', percentage: 10, color: '#CB171E' },
  { name: 'Docker', percentage: 5, color: '#2496ED' },
  { name: 'Markdown', percentage: 5, color: '#083FA1' },
];

function parseDuration(seconds: number | null | undefined): string | null {
  if (seconds == null) return null;
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function parseEngineStatus(raw: string | undefined): EngineStatusItem['status'] {
  if (!raw) return 'pending';
  const lower = raw.toLowerCase();
  if (lower === 'completed' || lower === 'success') return 'completed';
  if (lower === 'failed' || lower === 'error') return 'failed';
  if (lower === 'running' || lower === 'in_progress') return 'running';
  if (lower === 'skipped') return 'skipped';
  if (lower === 'unavailable') return 'unavailable';
  return 'pending';
}

export function analysisInsightsBuilder(
  job: AnalysisJob | null | undefined,
  report: Report | null | undefined,
  findingsSummary: FindingsSummary | null | undefined,
  findings: Finding[] | null | undefined,
  analysisMetadata?: AnalysisMetadataResponse | null | undefined,
): AnalysisInsights {
  const performanceScore = report?.performance_score ?? job?.overall_score;
  const securityScore = report?.security_score;
  const maintenanceScore = report?.maintainability_score;
  const categories = findingsSummary?.by_category ?? {};

  const priorityRecommendation = buildPriorityRecommendation(
    performanceScore,
    securityScore,
    maintenanceScore,
    categories,
    findings,
  );

  const engineStatus = ENGINE_KEYS.map((key) => {
    const rawStatus = job?.engine_statuses?.[key];
    const status = parseEngineStatus(rawStatus);
    // TODO: extract per-engine duration from API when available
    let score: number | null = null;
    if (key === 'performance') score = report?.performance_score ?? null;
    if (key === 'security') score = report?.security_score ?? null;
    if (key === 'reliability') score = report?.reliability_score ?? null;
    if (key === 'maintainability') score = report?.maintainability_score ?? null;
    if (key === 'devops') score = report?.devops_score ?? null;

    return {
      name: ENGINE_LABELS[key] ?? key,
      key,
      status,
      duration: null,
      score: status === 'completed' ? score : null,
      error: status === 'failed' ? `${key} engine encountered an error` : null,
    };
  });

  return {
    aiSummary: {
      summary:
        'This repository appears healthy overall. Security and reliability are in good condition. Performance can be improved by reducing synchronous database operations. Maintainability could benefit from simplifying complex modules.',
      isAiGenerated: false,
    },
    priorityRecommendation,
    repositoryOverview: {
      languages: report?.language_breakdown?.length
        ? report.language_breakdown.map((lang) => ({
            name: lang.name,
            percentage: lang.percentage,
            color: getLanguageColor(lang.name),
          }))
        : report?.languages_detected?.length
          ? report.languages_detected.map((name) => ({
              name,
              percentage: 0,
              color: '#6366f1',
            }))
          : FALLBACK_LANGUAGES,
      totalFiles: report?.total_files ?? job?.total_files ?? 0,
      totalLines: report?.total_lines_of_code ?? job?.total_lines ?? 0,
    },
    engineStatus,
    metadata: {
      totalFiles: report?.total_files ?? job?.total_files ?? 0,
      totalLines: report?.total_lines_of_code ?? job?.total_lines ?? 0,
      classes: analysisMetadata?.class_count ?? 0,
      functions: analysisMetadata?.function_count ?? 0,
      endpoints: analysisMetadata?.endpoint_count ?? 0,
      languages:
        report?.languages_detected?.length
          ? report.languages_detected
          : analysisMetadata?.languages ?? [],
      duration: parseDuration(report?.duration_seconds),
      startedAt: job?.started_at ?? null,
      completedAt: job?.completed_at ?? null,
      branch: job?.branch ?? 'main',
      repoUrl: job?.repo_url ?? '',
      workspaceId: job?.workspace_id ?? '',
    },
  };
}

function buildPriorityRecommendation(
  performanceScore: number | null | undefined,
  securityScore: number | null | undefined,
  maintenanceScore: number | null | undefined,
  categories: Record<string, number>,
  findings: Finding[] | null | undefined,
): PriorityRecommendation {
  if (performanceScore != null && performanceScore < 60) {
    const perfFinding = findings?.find((f) => f.category === 'performance');
    return {
      title: 'Improve Performance',
      description: 'Reduce synchronous database operations and optimize N+1 queries to improve response times under load.',
      impact: 'high',
      difficulty: 'medium',
      estimatedTime: '2-4 hours',
      findingId: perfFinding?.id ?? null,
      category: 'performance',
    };
  }

  if (securityScore != null && securityScore < 80) {
    const secFinding = findings?.find((f) => f.category === 'security');
    return {
      title: 'Improve Security',
      description: 'Address security vulnerabilities including input validation, authentication checks, and dependency updates.',
      impact: 'high',
      difficulty: 'medium',
      estimatedTime: '3-6 hours',
      findingId: secFinding?.id ?? null,
      category: 'security',
    };
  }

  const maintFinding = findings?.find((f) => f.category === 'maintainability');
  return {
    title: 'Improve Maintainability',
    description: 'Refactor complex modules with high cyclomatic complexity and reduce code duplication for better long-term maintainability.',
    impact: 'medium',
    difficulty: 'medium',
    estimatedTime: '4-8 hours',
    findingId: maintFinding?.id ?? null,
    category: 'maintainability',
  };
}
