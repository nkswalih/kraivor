import { getLanguageColor } from '@/lib/analysis/language-colors';
import { readEngineDuration, readEngineError, readEngineStatus } from '@/lib/analysis/engine-status';
import { JobStatus } from '@/types/domain/analysis';
import type {
  AnalysisInsights,
  AnalysisJob,
  AnalysisMetadata,
  AnalysisMetadataResponse,
  Report,
  RepositoryOverview,
  LanguageBar,
  FindingsSummary,
  Finding,
  EngineInfo,
  EngineStatusItem,
  PriorityRecommendation,
} from '@/types/domain/analysis';

/** The only status whose job is guaranteed to have a report row. */
const FINISHED_STATUS: JobStatus = JobStatus.COMPLETED;

/**
 * Whether a job is still being described by its job row rather than its report.
 *
 * Written as "is it finished?" rather than an allow-list of in-flight statuses
 * on purpose. A status added to the service later, or an unrecognised one, must
 * default to in flight: the alternative would treat a job with no report as
 * finished and read every field from a report that does not exist.
 *
 * `failed` lands on the in-flight side for the same reason. It has no report
 * either, but its job row still holds whatever was genuinely measured before it
 * stopped, and that is worth showing -- as nulls where nothing was reached.
 */
export function isJobInFlight(status: JobStatus | null | undefined): boolean {
  return status !== FINISHED_STATUS;
}

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

  // Which sources are legitimate depends on whether the run has a report yet.
  //
  // A finished job is described by its report: the report is built at finalize
  // from the scan, so it is the authoritative version of every number here. An
  // in-flight job has no report at all -- it is not written until the last
  // stage -- so reading from one would show nothing for the whole run and then
  // everything at once.
  //
  // For an in-flight job the honest sources are the job row (which the clone
  // stage fills in from 15%) and the metadata row (which the parse stage fills
  // in from 25%). Anything neither has measured yet is null, not zero.
  const reportDescribesRun = !isJobInFlight(job?.status);

  const repositoryOverview: RepositoryOverview = reportDescribesRun
    ? {
        languages: report?.language_breakdown?.length
          ? report.language_breakdown.map(langToBar)
          : report?.languages_detected?.length
            ? report.languages_detected.map(nameToBar)
            : null,
        totalFiles: report?.total_files ?? job?.total_files ?? null,
        totalLines: report?.total_lines_of_code ?? job?.total_lines ?? null,
      }
    : {
        languages: job?.language_breakdown?.length
          ? job.language_breakdown.map(langToBar)
          : null,
        totalFiles: job?.total_files ?? null,
        totalLines: job?.total_lines ?? null,
      };

  const metadata: AnalysisMetadata = {
    totalFiles: reportDescribesRun
      ? report?.total_files ?? job?.total_files ?? null
      : job?.total_files ?? null,
    totalLines: reportDescribesRun
      ? report?.total_lines_of_code ?? job?.total_lines ?? null
      : job?.total_lines ?? null,
    classes: reportDescribesRun ? analysisMetadata?.class_count ?? null : null,
    functions: reportDescribesRun ? analysisMetadata?.function_count ?? null : null,
    endpoints: reportDescribesRun ? analysisMetadata?.endpoint_count ?? null : null,
    // `language_breakdown` first while the run is in flight: the job row carries
    // it from 15%, whereas the metadata row's copy does not appear until 25%.
    languages: reportDescribesRun
      ? report?.languages_detected?.length
        ? report.languages_detected
        : analysisMetadata?.languages ?? null
      : job?.languages_detected?.length
        ? job.languages_detected
        : null,
    duration: reportDescribesRun ? parseDuration(report?.duration_seconds) : null,
    startedAt: job?.started_at ?? null,
    completedAt: job?.completed_at ?? null,
    // Not defaulted to 'main'. The start request defaults the branch to main, but
    // a job row that never recorded one is missing it rather than on main.
    branch: present(job?.branch),
    repoUrl: present(job?.repo_url),
    workspaceId: present(job?.workspace_id),
  };

  return {
    aiSummary: {
      summary: aiExecutiveSummary ?? '',
      isAiGenerated: hasAiSummary,
    },
    priorityRecommendation,
    repositoryOverview,
    engineStatus,
    metadata,
  };
}

/**
 * An empty string is absence, not a value.
 *
 * The API can hand back `""` for a column that was never filled, and rendering
 * that is rendering nothing. Normalised to null so a card shows its em-dash
 * rather than a blank that looks like a rendering fault.
 */
function present(value: string | null | undefined): string | null {
  return value ? value : null;
}

function langToBar(lang: { name: string; percentage: number }): LanguageBar {
  return {
    name: lang.name,
    percentage: lang.percentage,
    color: getLanguageColor(lang.name),
  };
}

/**
 * A language known by name before its share is known.
 *
 * Only reachable on a completed report, where `languages_detected` is populated
 * and `language_breakdown` is not. The share is genuinely unknown, so it is
 * left at zero -- the bar renders as no width rather than inventing a figure.
 */
function nameToBar(name: string): LanguageBar {
  return { name, percentage: 0, color: '#6366f1' };
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
