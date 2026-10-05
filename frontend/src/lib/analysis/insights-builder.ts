import { getLanguageColor } from '@/lib/analysis/language-colors';
import { readEngineDuration, readEngineError, readEngineStatus } from '@/lib/analysis/engine-status';
import type {
  AnalysisInsights,
  AnalysisJob,
  AnalysisMetadataResponse,
  Report,
  FindingsSummary,
  Finding,
  EngineInfo,
  EngineStatusItem,
  PriorityRecommendation,
} from '@/types/domain/analysis';

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
  aiExecutiveSummary?: string | null | undefined,
  engines?: EngineInfo[] | null | undefined,
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

  // Engines come from the service's catalogue. This file used to keep its own
// list of 6, which is how dead_code, error_detection and churn ended up
// invisible while doing real work. Until the catalogue arrives, fall back to
// whatever the job actually reports rather than a second hardcoded guess.
const engineList: EngineInfo[] =
  engines?.length
    ? engines
    : Object.keys(job?.engine_statuses ?? {}).map(key => ({
        key,
        label: key,
        description: '',
        stage: '',
        score_category: null,
      }));

const engineStatus = engineList.map(engine => {
    const key = engine.key;
    const status = parseEngineStatus(readEngineStatus(job?.engine_statuses, key));
    // score_category is the engine's scoring dimension, so the score lookup is
    // derived rather than a per-key table that could drift out of step.
    const score =
      engine.score_category != null
        ? ((report?.[`${engine.score_category}_score` as keyof Report] as
            | number
            | null
            | undefined) ?? null)
        : null;

    return {
      name: engine.label,
      key,
      description: engine.description,
      status,
      // Real timing now that the service records each engine's window. Was a
      // hardcoded null with a TODO waiting on exactly this.
      duration: readEngineDuration(job?.engine_statuses, key),
      score: status === 'completed' ? score : null,
      error: readEngineError(job?.engine_statuses, key),
    };
  });

  const hasAiSummary = !!aiExecutiveSummary && aiExecutiveSummary.trim().length > 0;

  return {
    aiSummary: {
      summary: aiExecutiveSummary ?? '',
      isAiGenerated: hasAiSummary,
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

  const qualityCount = categories['quality'] ?? 0;
  if (qualityCount >= 5) {
    const qualityFinding = findings?.find((f) => f.category === 'quality');
    return {
      title: 'Refactor Churn Hotspots',
      description: 'Files with high change frequency and spread ownership are at risk of architectural decay. Consider refactoring hotspot files to improve maintainability.',
      impact: 'medium',
      difficulty: 'medium',
      estimatedTime: '3-6 hours',
      findingId: qualityFinding?.id ?? null,
      category: 'quality',
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
