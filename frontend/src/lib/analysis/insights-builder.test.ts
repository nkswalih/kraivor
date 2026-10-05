import { describe, it, expect } from 'vitest';
import { analysisInsightsBuilder, isJobInFlight } from './insights-builder';
import { JobStatus, Category, Severity } from '@/types/domain/analysis';
import type {
  AnalysisJob,
  AnalysisMetadataResponse,
  Report,
  FindingsSummary,
  Finding,
  EngineInfo,
  AiSummaryError,
} from '@/types/domain/analysis';

// ======================================================================
// Builders
// ======================================================================

function job(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    job_id: 'job-1',
    repo_id: 'repo-1',
    workspace_id: 'ws-1',
    status: JobStatus.PARSING,
    repo_url: 'https://github.com/acme/widget',
    branch: 'feature/x',
    progress_pct: 40,
    progress_message: 'Parsing files... (8/20)',
    total_findings: 0,
    total_files: null,
    total_lines: null,
    overall_score: null,
    blocked_by: [],
    engine_statuses: {},
    error_message: null,
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:05Z',
    completed_at: null,
    languages_detected: null,
    language_breakdown: null,
    ...overrides,
  };
}

function report(overrides: Partial<Report> = {}): Report {
  return {
    job_id: 'job-1',
    repo_id: 'repo-1',
    workspace_id: 'ws-1',
    branch: 'main',
    overall_score: 82,
    performance_score: 80,
    security_score: 75,
    reliability_score: 85,
    maintainability_score: 82,
    devops_score: 80,
    total_findings: 5,
    total_files: 120,
    total_lines_of_code: 8400,
    languages_detected: ['Python', 'Go'],
    language_breakdown: [
      { name: 'Python', percentage: 70.5 },
      { name: 'Go', percentage: 29.5 },
    ],
    duration_seconds: 95,
    completed_at: '2026-01-01T00:01:40Z',
    report_url: null,
    ...overrides,
  };
}

function meta(overrides: Partial<AnalysisMetadataResponse> = {}): AnalysisMetadataResponse {
  return {
    job_id: 'job-1',
    class_count: 30,
    function_count: 210,
    endpoint_count: 12,
    languages: ['Python', 'Go'],
    frameworks: ['fastapi'],
    ...overrides,
  };
}

const NO_SUMMARY = null as FindingsSummary | null;
const NO_FINDINGS = null;

function finding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 'f-1',
    job_id: 'job-1',
    rule_id: 'PERF-001',
    category: Category.QUALITY,
    severity: Severity.HIGH,
    title: 'Churn hotspot',
    description: 'Changed by many authors in a short period.',
    recommendation: 'Split the module.',
    enterprise_pattern: 'Ownership spread',
    file_path: 'src/hot.py',
    line_start: 1,
    line_end: 20,
    status: 'active',
    code_snippet: 'def hot(): ...',
    score_impact: -3,
    rpm_impact: 0,
    is_ai_enriched: false,
    ...overrides,
  };
}

/** The in-flight case: a running job, no report yet. */
function running(
  j: Partial<AnalysisJob> = {},
  m: Partial<AnalysisMetadataResponse> | null = null,
) {
  return analysisInsightsBuilder(
    job(j),
    null,
    NO_SUMMARY,
    NO_FINDINGS,
    m ? meta(m) : null,
    null,
    null,
  );
}

/**
 * The finished case: a completed job with its report and its metadata row.
 *
 * A completed run always has both -- the report at finalize, the metadata row
 * from the parse stage -- so the default here passes a real metadata row rather
 * than leaving it out. A test that wants it absent says so explicitly.
 */
function finished(
  r: Partial<Report> = {},
  m: Partial<AnalysisMetadataResponse> | null | undefined = undefined,
  j: Partial<AnalysisJob> = {},
) {
  return analysisInsightsBuilder(
    job({ status: JobStatus.COMPLETED, completed_at: '2026-01-01T00:01:40Z', ...j }),
    report(r),
    NO_SUMMARY,
    NO_FINDINGS,
    m === null ? null : meta(m ?? {}),
    null,
    null,
  );
}

// ======================================================================
// Run state
// ======================================================================

describe('isJobInFlight', () => {
  it.each([
    JobStatus.QUEUED,
    JobStatus.CLONING,
    JobStatus.PARSING,
    JobStatus.RULES,
    JobStatus.DEAD_CODE,
    JobStatus.ERRORS,
    JobStatus.PERF,
    JobStatus.SIMULATION,
    JobStatus.SCORING,
    JobStatus.GUIDE_GEN,
  ])('treats %s as in flight', (status) => {
    expect(isJobInFlight(status)).toBe(true);
  });

  it('treats a completed job as finished', () => {
    expect(isJobInFlight(JobStatus.COMPLETED)).toBe(false);
  });

  it('treats a failed job as in flight, because it has no report', () => {
    // A failed job has no report row, so the report-driven branch would read
    // every field as absent while the job row still holds what was genuinely
    // measured before it stopped.
    expect(isJobInFlight(JobStatus.FAILED)).toBe(true);
  });

  it('treats an unknown status as in flight, not finished', () => {
    // Treating an unrecognised status as finished would silently reintroduce
    // report-only reads on a job that has no report yet. This is the case that
    // makes the helper "is it finished?" rather than an in-flight allow-list.
    expect(isJobInFlight('something-new' as JobStatus)).toBe(true);
  });

  it('treats an absent status as in flight', () => {
    expect(isJobInFlight(null)).toBe(true);
    expect(isJobInFlight(undefined)).toBe(true);
  });
});

describe('a failed job still shows what it measured', () => {
  it('reads the job row, not a report that was never written', () => {
    const insights = analysisInsightsBuilder(
      job({
        status: JobStatus.FAILED,
        total_files: 40,
        languages_detected: ['Go'],
        language_breakdown: [{ name: 'Go', percentage: 100 }],
      }),
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      null,
    );

    expect(insights.repositoryOverview.totalFiles).toBe(40);
    expect(insights.repositoryOverview.languages?.map(l => l.name)).toEqual(['Go']);
    // Reached-but-unmeasured stays null on a failed run too.
    expect(insights.metadata.classes).toBeNull();
    expect(insights.metadata.duration).toBeNull();
  });
});

// ======================================================================
// The defect: fabricated values for a job that has measured nothing
// ======================================================================

describe('an in-flight job reports no invented figures', () => {
  it('shows no language bar at all before clone has run', () => {
    // The old builder fell back to a hardcoded Python/TypeScript/YAML/Docker/
    // Markdown list at 60/20/10/5/5. Every one of those was fiction, and
    // `null` is the only honest answer at 0%.
    const insights = running();

    expect(insights.repositoryOverview.languages).toBeNull();
  });

  it('shows no file or line count before clone has run', () => {
    const insights = running();

    expect(insights.repositoryOverview.totalFiles).toBeNull();
    expect(insights.repositoryOverview.totalLines).toBeNull();
  });

  it('shows no class, function or endpoint count before parse has run', () => {
    // The old builder defaulted all three to 0, which reads as "this repository
    // has no classes" rather than "this has not been counted yet".
    const insights = running();

    expect(insights.metadata.classes).toBeNull();
    expect(insights.metadata.functions).toBeNull();
    expect(insights.metadata.endpoints).toBeNull();
  });

  it('shows no language list before clone has run', () => {
    const insights = running();

    expect(insights.metadata.languages).toBeNull();
  });

  it('shows no duration before the run has finished', () => {
    // A duration on a running job is either zero or a fabrication; the report
    // carries it and the report only exists at the end.
    const insights = running();

    expect(insights.metadata.duration).toBeNull();
  });

  it('keeps the branch the job actually recorded', () => {
    const insights = running({ branch: 'release/2.1' });

    expect(insights.metadata.branch).toBe('release/2.1');
  });

  it('does not default an unrecorded branch to main', () => {
    const insights = running({ branch: undefined as unknown as string });

    expect(insights.metadata.branch).toBeNull();
  });

  it('keeps an unrecorded repository url null rather than empty', () => {
    const insights = running({ repo_url: '' });

    expect(insights.metadata.repoUrl).toBeNull();
  });

  it('never reads the report for an in-flight job', () => {
    // A report arriving early (a stale cache, a previous run) must not be
    // mistaken for this run's results.
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.PARSING, total_files: 12 }),
      report({ total_files: 9999, total_lines_of_code: 999999 }),
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      null,
    );

    expect(insights.repositoryOverview.totalFiles).toBe(12);
    expect(insights.repositoryOverview.totalLines).toBeNull();
  });

  it('still surfaces what the job row genuinely holds mid-run', () => {
    const insights = running({
      total_files: 120,
      total_lines: 8400,
      languages_detected: ['Python', 'Go'],
      language_breakdown: [
        { name: 'Python', percentage: 70.5 },
        { name: 'Go', percentage: 29.5 },
      ],
    });

    expect(insights.repositoryOverview.totalFiles).toBe(120);
    expect(insights.repositoryOverview.totalLines).toBe(8400);
    expect(insights.metadata.languages).toEqual(['Python', 'Go']);
    expect(insights.repositoryOverview.languages?.map(l => l.name)).toEqual([
      'Python',
      'Go',
    ]);
  });

  it('prefers the job row breakdown over the metadata row copy', () => {
    // The job row carries languages from 15%, the metadata row's copy from 25%.
    const insights = running(
      { language_breakdown: [{ name: 'Rust', percentage: 100 }] },
      { languages: ['Python', 'Go'] },
    );

    expect(insights.repositoryOverview.languages?.map(l => l.name)).toEqual(['Rust']);
  });
});

describe('an in-flight job does not use the metadata row for counts', () => {
  it('leaves counts null even when a metadata row exists', () => {
    // The metadata row is written from 25%. Reading it during an earlier stage
    // would show counts the run has not produced, and would make the counts
    // flicker from zero to real with no relation to progress.
    const insights = running({}, { class_count: 30, function_count: 210 });

    expect(insights.metadata.classes).toBeNull();
    expect(insights.metadata.functions).toBeNull();
  });
});

// ======================================================================
// A finished job must not change
// ======================================================================

describe('a completed job is unchanged', () => {
  it('reads its figures from the report', () => {
    const insights = finished();

    expect(insights.repositoryOverview.totalFiles).toBe(120);
    expect(insights.repositoryOverview.totalLines).toBe(8400);
    expect(insights.metadata.classes).toBe(30);
    expect(insights.metadata.functions).toBe(210);
    expect(insights.metadata.endpoints).toBe(12);
    expect(insights.metadata.duration).toBe('1m 35s');
  });

  it('renders the report language breakdown with its percentages', () => {
    const insights = finished();

    expect(insights.repositoryOverview.languages).toEqual([
      { name: 'Python', percentage: 70.5, color: expect.any(String) },
      { name: 'Go', percentage: 29.5, color: expect.any(String) },
    ]);
  });

  it('lists the languages the report detected', () => {
    const insights = finished();

    expect(insights.metadata.languages).toEqual(['Python', 'Go']);
  });

  it('shows the recorded timestamps', () => {
    const insights = finished();

    expect(insights.metadata.startedAt).toBe('2026-01-01T00:00:05Z');
    expect(insights.metadata.completedAt).toBe('2026-01-01T00:01:40Z');
  });

  it('does not invent a language list when the report has none', () => {
    // This is the one place a completed job's behaviour changed: the hardcoded
    // five used to appear here. An empty report now says nothing measured
    // anything, which is what the data supports.
    const insights = finished({ language_breakdown: [], languages_detected: [] });

    expect(insights.repositoryOverview.languages).toBeNull();
  });

  it('keeps the name-only fallback for a report with names but no shares', () => {
    const insights = finished({
      language_breakdown: [],
      languages_detected: ['Elixir'],
    });

    expect(insights.repositoryOverview.languages).toEqual([
      { name: 'Elixir', percentage: 0, color: '#6366f1' },
    ]);
  });
});

// ======================================================================
// The priority recommendation
// ======================================================================

describe('no recommendation is invented for a run that has measured nothing', () => {
  it('recommends nothing while the job is in flight', () => {
    // The old builder always returned something. With no scores, no category
    // counts and no findings, every branch fell through to the last one, and a
    // repository nobody had scored was told to refactor for maintainability
    // with a medium impact rating and a four-to-eight hour estimate.
    const insights = running();

    expect(insights.priorityRecommendation).toBeNull();
  });

  it('recommends nothing for a job that has not started', () => {
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.QUEUED }),
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      null,
    );

    expect(insights.priorityRecommendation).toBeNull();
  });

  it('recommends nothing for a failed job', () => {
    // A failed run has no scores, so the same fall-through would apply.
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.FAILED }),
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      null,
    );

    expect(insights.priorityRecommendation).toBeNull();
  });

  it('stays silent even when the job row carries an overall score', () => {
    // A single score is not enough. The card matches on three dimensions plus
    // category counts, and the remaining inputs are absent mid-run, so any
    // recommendation now would rest on one number.
    const insights = running({ overall_score: 42 });

    expect(insights.priorityRecommendation).toBeNull();
  });

  it('stays silent even when findings have arrived early', () => {
    // Findings are written by the engine stages, so a job partway through can
    // legitimately have some. Without scores there is still no ranking to place
    // them in.
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.ERRORS }),
      null,
      { job_id: 'job-1', total: 1, by_severity: { high: 1 }, by_category: { quality: 9 } },
      [finding()],
      null,
      null,
      null,
    );

    expect(insights.priorityRecommendation).toBeNull();
  });
});

describe('a completed job keeps its recommendation unchanged', () => {
  it('recommends performance work for a low performance score', () => {
    const insights = finished({ performance_score: 45 });

    expect(insights.priorityRecommendation).toMatchObject({
      title: 'Improve Performance',
      impact: 'high',
      difficulty: 'medium',
      estimatedTime: '2-4 hours',
      category: 'performance',
    });
  });

  it('recommends security work for a low security score', () => {
    const insights = finished({ performance_score: 90, security_score: 60 });

    expect(insights.priorityRecommendation).toMatchObject({
      title: 'Improve Security',
      estimatedTime: '3-6 hours',
      category: 'security',
    });
  });

  it('recommends churn work when quality findings pile up', () => {
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.COMPLETED }),
      report({ performance_score: 90, security_score: 90 }),
      { job_id: 'job-1', total: 7, by_severity: {}, by_category: { quality: 7 } },
      NO_FINDINGS,
      null,
      null,
      null,
    );

    expect(insights.priorityRecommendation).toMatchObject({
      title: 'Refactor Churn Hotspots',
      category: 'quality',
    });
  });

  it('falls through to maintainability when nothing else applies', () => {
    // Kept deliberately. This is the card's only remaining advice and it is
    // what every well-scoring run has always been told; changing it is a
    // different task from removing the fabrications from a running job.
    const insights = finished({ performance_score: 95, security_score: 95 });

    expect(insights.priorityRecommendation).toMatchObject({
      title: 'Improve Maintainability',
      estimatedTime: '4-8 hours',
    });
  });

  it('links the recommendation to a real finding when one matches', () => {
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.COMPLETED }),
      report({ performance_score: 45 }),
      NO_SUMMARY,
      [finding({ id: 'f-99', category: Category.PERFORMANCE })],
      null,
      null,
      null,
    );

    expect(insights.priorityRecommendation?.findingId).toBe('f-99');
  });

  it('leaves the finding link null when no finding matches', () => {
    expect(finished({ performance_score: 45 }).priorityRecommendation?.findingId).toBeNull();
  });
});

// ======================================================================
// Engine status is unaffected by the branch
// ======================================================================

describe('engine status still comes from the catalogue', () => {
  const engines: EngineInfo[] = [
    { key: 'security', label: 'Security', description: 'Injection and secrets.', stage: 'rules', score_category: 'security' },
    { key: 'churn', label: 'Churn', description: 'Change hotspots.', stage: 'churn', score_category: null },
  ];

  it('lists catalogue engines for a running job', () => {
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.RULES }),
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      engines,
    );

    expect(insights.engineStatus.map(e => e.key)).toEqual(['security', 'churn']);
    expect(insights.engineStatus[0].description).toBe('Injection and secrets.');
  });

  it('shows no score for an engine that has not completed', () => {
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.RULES }),
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      engines,
    );

    expect(insights.engineStatus[0].status).toBe('pending');
    expect(insights.engineStatus[0].score).toBeNull();
  });

  it('derives the score from the engine scoring dimension', () => {
    // Both engines recorded as completed, because an engine only scores once it
    // has finished -- the builder gates the score on that.
    const insights = analysisInsightsBuilder(
      job({
        status: JobStatus.SCORING,
        engine_statuses: {
          security: { status: 'completed', started_at: null, ended_at: null, error: '' },
          churn: { status: 'completed', started_at: null, ended_at: null, error: '' },
        },
      }),
      report(),
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      engines,
    );

    const security = insights.engineStatus.find(e => e.key === 'security');
    expect(security?.status).toBe('completed');
    expect(security?.score).toBe(75);
  });

  it('leaves the score null for an engine with no scoring dimension', () => {
    const insights = analysisInsightsBuilder(
      job({
        status: JobStatus.SCORING,
        engine_statuses: {
          security: { status: 'completed', started_at: null, ended_at: null, error: '' },
          churn: { status: 'completed', started_at: null, ended_at: null, error: '' },
        },
      }),
      report(),
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      engines,
    );

    // `churn` has `score_category: null`, so there is no column to read even
    // though the job completed.
    expect(insights.engineStatus.find(e => e.key === 'churn')?.score).toBeNull();
  });
});

// ======================================================================
// The running progress panel's view of the same rows
// ======================================================================

/**
 * The job detail page renders these rows as a *sequence* rather than a grid, so
 * three properties of this output are load-bearing there and are not visible in
 * the sidebar: the order the pipeline runs in, each engine's recorded duration,
 * and the reason a failed engine failed. All three used to reach the running view
 * from `engine-card.tsx`, which had neither the order nor the duration.
 */
describe('engineStatus for the running progress panel', () => {
  // Deliberately not alphabetical, and not the order the engines appear in the
  // job's status map below. If the builder sorted or fell back to map order, the
  // step list would stop being a sequence.
  const pipelineOrder: EngineInfo[] = [
    { key: 'simulation', label: 'Simulation', description: 'Runtime behaviour.', stage: 'simulation', score_category: null },
    { key: 'churn', label: 'Churn', description: 'Change hotspots.', stage: 'churn', score_category: null },
    { key: 'security', label: 'Security', description: 'Injection and secrets.', stage: 'rules', score_category: 'security' },
    { key: 'error_detection', label: 'Error detection', description: 'Linting and compile errors.', stage: 'errors', score_category: null },
  ];

  const runningJob = job({
    status: JobStatus.ERRORS,
    engine_statuses: {
      // Written in yet another order, to catch anything that reads the map
      // directly for its ordering.
      security: {
        status: 'running',
        started_at: '2026-01-01T00:00:30Z',
        ended_at: null,
        error: '',
      },
      churn: {
        status: 'completed',
        started_at: '2026-01-01T00:00:10Z',
        ended_at: '2026-01-01T00:00:14Z',
        error: '',
      },
      simulation: {
        status: 'skipped',
        started_at: null,
        ended_at: null,
        error: '',
      },
      error_detection: {
        status: 'failed',
        started_at: '2026-01-01T00:00:20Z',
        ended_at: '2026-01-01T00:00:22Z',
        error: 'ruff exited 2: config file missing',
      },
    },
  });

  it('orders the rows as the pipeline does, not alphabetically and not by status map', () => {
    const insights = analysisInsightsBuilder(
      runningJob,
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      pipelineOrder,
    );

    // Rendered as an ordered list with connectors between steps, so the order is
    // the sequence a reader follows. Getting this wrong would show the run's
    // steps in an order no pipeline produces.
    expect(insights.engineStatus.map(e => e.key)).toEqual([
      'simulation',
      'churn',
      'security',
      'error_detection',
    ]);
  });

  it('carries each engine duration through from the status map', () => {
    const insights = analysisInsightsBuilder(
      runningJob,
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      pipelineOrder,
    );

    // The step component renders this and nothing else, so a builder that left
    // it null would show a finished engine with no time beside it at all.
    expect(insights.engineStatus.find(e => e.key === 'churn')?.duration).toBe('4s');
    expect(insights.engineStatus.find(e => e.key === 'error_detection')?.duration).toBe('2s');
  });

  it('reports no duration for the engine that is still running', () => {
    const insights = analysisInsightsBuilder(
      runningJob,
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      pipelineOrder,
    );

    // There is no end time yet. The step counts its own time from the start, and
    // a stale `null` here would be shown as "Measuring" for a run that is 30
    // seconds in.
    expect(insights.engineStatus.find(e => e.key === 'security')?.duration).toBeNull();
  });

  it('carries a failed engine error through for display', () => {
    const insights = analysisInsightsBuilder(
      runningJob,
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      pipelineOrder,
    );

    // The service recorded a specific reason. Dropping it here is what left the
    // old card saying "Engine encountered errors during scan" for all five of its
    // hardcoded engines.
    expect(insights.engineStatus.find(e => e.key === 'error_detection')?.error).toBe(
      'ruff exited 2: config file missing',
    );
  });

  it('reports a skipped engine as skipped, with no error and no score', () => {
    const insights = analysisInsightsBuilder(
      runningJob,
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      pipelineOrder,
    );

    const simulation = insights.engineStatus.find(e => e.key === 'simulation');
    expect(simulation?.status).toBe('skipped');
    expect(simulation?.error).toBeNull();
    expect(simulation?.score).toBeNull();
  });

  it('falls back to the job\'s own engine keys when the catalogue has not loaded', () => {
    // The catalogue request and the job request race. Showing nothing while they
    // do would blank the panel on every page load, and listing a guessed set of
    // engines would be the old defect wearing a new hat.
    const insights = analysisInsightsBuilder(
      runningJob,
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      null,
    );

    expect(insights.engineStatus.map(e => e.key).sort()).toEqual([
      'churn',
      'error_detection',
      'security',
      'simulation',
    ]);
    // No catalogue, so no label and no description to show.
    expect(insights.engineStatus.find(e => e.key === 'security')?.name).toBe('security');
    expect(insights.engineStatus.find(e => e.key === 'security')?.description).toBe('');
  });

  it('still reports a status for every catalogue engine, not only the ones the job knows', () => {
    const insights = analysisInsightsBuilder(
      job({ status: JobStatus.PARSING, engine_statuses: {} }),
      null,
      NO_SUMMARY,
      NO_FINDINGS,
      null,
      null,
      pipelineOrder,
    );

    // A queued job has an empty status map. The panel must still show every
    // engine as waiting, which is the answer -- not an empty list.
    expect(insights.engineStatus).toHaveLength(4);
    expect(insights.engineStatus.every(e => e.status === 'pending')).toBe(true);
  });
});

// ======================================================================
// The summary's failure
// ======================================================================

describe('The summary failure', () => {
  const FAILURE: AiSummaryError = {
    code: 'provider_not_configured',
    message: 'No provider key is configured.',
    suggested_action: 'add_key',
  };

  /** A finished run with the eighth argument being `failure`. */
  function withFailure(failure: AiSummaryError | null, summary: string | null = null) {
    return analysisInsightsBuilder(
      job({ status: JobStatus.COMPLETED, completed_at: '2026-01-01T00:01:40Z' }),
      report({}),
      NO_SUMMARY,
      NO_FINDINGS,
      meta({}),
      summary,
      null,
      failure,
    );
  }

  it('carries the reason through when there is no summary', () => {
    // This is the whole point of the eighth argument. Before it, a finished run
    // with no summary and a finished run whose summary could not be generated
    // both arrived as `summary: ''` and rendered the same empty card.
    expect(withFailure(FAILURE).aiSummary.error).toEqual(FAILURE);
  });

  it('drops the reason when a summary exists', () => {
    // A summary and a reason together mean the summary is stale, which the guide
    // section renders as such. The sidebar card cannot: it renders one body, and
    // choosing between the summary and the reason here would either hide the work
    // that succeeded or hide the reason. So the builder picks for that surface,
    // and the section takes both props directly.
    expect(withFailure(FAILURE, '## Assessment\n\nFine.').aiSummary.error).toBeNull();
  });

  it('reports no error for a run that never attempted one', () => {
    // Distinguishable from the above, and the distinction is what lets the card
    // say "not available, click regenerate" rather than naming a failure that did
    // not happen.
    const insights = withFailure(null);

    expect(insights.aiSummary.error).toBeNull();
    expect(insights.aiSummary.isAiGenerated).toBe(false);
  });

  it('treats a whitespace-only summary as absent', () => {
    // The API can hand back a column that was written but is blank. Rendering
    // that is rendering nothing, and pairing it with a reason would claim the
    // summary is bad when there is not one.
    const insights = withFailure(FAILURE, '   \n  ');

    expect(insights.aiSummary.isAiGenerated).toBe(false);
    expect(insights.aiSummary.error).toEqual(FAILURE);
  });
});
