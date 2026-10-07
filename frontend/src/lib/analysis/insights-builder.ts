import { getLanguageColor } from '@/lib/analysis/language-colors';
import { readEngineDuration, readEngineError, readEngineStatus } from '@/lib/analysis/engine-status';
import { JobStatus } from '@/types/domain/analysis';
import type {
  AnalysisInsights,
  AnalysisJob,
  AnalysisMetadata,
  AnalysisMetadataResponse,
  AiSummaryError,
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
  aiSummaryError?: AiSummaryError | null | undefined,
): AnalysisInsights {
  // The card quotes one finding: this run's worst active one, fetched as a
  // single row that the repository orders worst-first in SQL. This function
  // used to pick a *problem area* from the scores -- performance under 60
  // meant "performance" -- and print whichever template belonged to that
  // area, on runs where no rule had ever filed a finding in it. A score can
  // be low with no evidence behind it; the findings are the evidence, and
  // with none there is nothing to recommend. Null is that answer, and the
  // card renders it honestly rather than filling the space.
  const priorityRecommendation = isJobInFlight(job?.status)
    ? null
    : buildPriorityRecommendation(findings);

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

  // A summary and a reason are mutually exclusive on the wire, but the pair is
  // normalised here rather than in the card because this is the one place that
  // can see both: a re-enrich that failed keeps the previous summary (a paying
  // user should not lose one because a regenerate failed) and records the new
  // reason beside it. `error: null` in that case is load-bearing -- it is what
  // tells the card the summary it is about to render is stale.
  //
  // A reason without a missing summary is dropped. It cannot arise from a
  // correct write, and rendering it next to a summary would claim the summary is
  // bad when the write that produced it was.
  const summaryError = hasAiSummary ? null : (aiSummaryError ?? null);

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

  // The shape counts come from the same parse-stage row `metadata` reads below,
  // and are deliberately the same four numbers: Repository Overview is where
  // they are shown as figures, and the run record repeats them as rows. Both
  // stay null until the stage that takes them has run -- a completed run whose
  // parse never produced a row has no count, not a zero.
  const repositoryOverview: RepositoryOverview = reportDescribesRun
    ? {
        languages: report?.language_breakdown?.length
          ? report.language_breakdown.map(langToBar)
          : report?.languages_detected?.length
            ? report.languages_detected.map(nameToBar)
            : null,
        totalFiles: report?.total_files ?? job?.total_files ?? null,
        totalLines: report?.total_lines_of_code ?? job?.total_lines ?? null,
        classes: analysisMetadata?.class_count ?? null,
        functions: analysisMetadata?.function_count ?? null,
        endpoints: analysisMetadata?.endpoint_count ?? null,
        frameworks: analysisMetadata?.frameworks?.length ?? null,
      }
    : {
        languages: job?.language_breakdown?.length
          ? job.language_breakdown.map(langToBar)
          : null,
        totalFiles: job?.total_files ?? null,
        totalLines: job?.total_lines ?? null,
        classes: null,
        functions: null,
        endpoints: null,
        frameworks: null,
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
      error: summaryError,
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
 *
 * The colour used to be a hardcoded indigo for every one of them, so a report
 * in this state drew a bar of identical segments and a legend of identical
 * dots: every language indistinguishable from every other, which is the one
 * thing a language legend must not be. `getLanguageColor` has the answer, and
 * it already handles a name it has never heard of.
 */
function nameToBar(name: string): LanguageBar {
  return { name, percentage: 0, color: getLanguageColor(name) };
}

/** Worst first. An unrecognised severity sorts last rather than throwing. */
const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

/**
 * The three chips, as estimates keyed on how bad the finding is.
 *
 * A `Finding` records no effort data -- there is no hours field on it and no
 * size estimate anywhere upstream -- so anything shown here is an estimate and
 * is labelled as one on the card. Severity is the only ranking the finding does
 * carry, and it is the one a reviewer already uses to decide what to open
 * first, so the effort is keyed off it rather than invented per category.
 *
 * `impact` is the exception in spirit but not in mechanism: severity *is* the
 * impact statement, so that chip stops being an estimate at all.
 */
const EFFORT_BY_SEVERITY: Record<
  string,
  Pick<PriorityRecommendation, 'impact' | 'difficulty' | 'estimatedTime'>
> = {
  critical: { impact: 'high', difficulty: 'high', estimatedTime: '1-2 days' },
  high: { impact: 'high', difficulty: 'medium', estimatedTime: '3-6 hours' },
  medium: { impact: 'medium', difficulty: 'medium', estimatedTime: '2-4 hours' },
  low: { impact: 'low', difficulty: 'low', estimatedTime: '1-2 hours' },
  info: { impact: 'low', difficulty: 'low', estimatedTime: 'Under 1 hour' },
};

/** Kept out of the table only so an unrecognised severity has something to read. */
const MEDIUM_EFFORT = EFFORT_BY_SEVERITY.medium ?? {
  impact: 'medium' as const,
  difficulty: 'medium' as const,
  estimatedTime: '2-4 hours',
};

/**
 * The finding the card should describe.
 *
 * Active only: a dismissed finding was looked at and set aside by somebody, and
 * recommending it back to them is the card arguing with a decision.
 *
 * The repository now orders its rows worst-first, so the card's `page_size: 1`
 * hands this exactly the answer it would compute. The ranking stays here as
 * well -- severity, then how much score the finding costs, then id -- so a
 * caller that passes several rows still gets the one the server would have put
 * first, and so the two definitions of "worst" are visible side by side.
 */
function worstFindingIn(findings: Finding[] | null | undefined): Finding | null {
  const candidates = (findings ?? []).filter((f) => f.status === 'active');
  if (candidates.length === 0) return null;

  return candidates.reduce((worst, candidate) => {
    const rankGap =
      (SEVERITY_RANK[worst.severity] ?? Number.MAX_SAFE_INTEGER) -
      (SEVERITY_RANK[candidate.severity] ?? Number.MAX_SAFE_INTEGER);
    if (rankGap !== 0) return rankGap < 0 ? worst : candidate;
    if (candidate.score_impact !== worst.score_impact) {
      return candidate.score_impact < worst.score_impact ? candidate : worst;
    }
    return candidate.id < worst.id ? candidate : worst;
  });
}

function buildPriorityRecommendation(
  findings: Finding[] | null | undefined,
): PriorityRecommendation | null {
  const worst = worstFindingIn(findings);
  // No active finding is a real result, not a gap to fill: the card shows the
  // run's empty state instead of advice nobody measured.
  if (!worst) return null;

  // Content from the finding: its own words about what is wrong and what to
  // do, in the order the card has always quoted them. Fields missing fall
  // through to the next, and the last resort is the rule id -- the finding
  // addressing itself -- and then its area. Never a sentence invented here.
  const title =
    firstNonEmpty(worst.recommendation, worst.title, worst.rule_id) ??
    worst.category;
  const description = firstNonEmpty(worst.description, worst.title) ?? title;
  const effort = EFFORT_BY_SEVERITY[worst.severity] ?? MEDIUM_EFFORT;

  return {
    title,
    description,
    impact: effort.impact,
    difficulty: effort.difficulty,
    estimatedTime: effort.estimatedTime,
    findingId: worst.id,
    // The finding's own area, so the icon on the card describes the advice it
    // quotes.
    category: worst.category,
    severity: worst.severity,
    filePath: worst.file_path,
    lineStart: worst.line_start,
  };
}

/** First value that survives a trim, or null when none do. */
function firstNonEmpty(...values: (string | null | undefined)[]): string | null {
  for (const value of values) {
    const trimmed = value?.trim();
    if (trimmed) return trimmed;
  }
  return null;
}
