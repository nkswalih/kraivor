import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { ProjectContextCard, formatElapsed } from './ProjectContextCard';
import { JobStatus } from '@/types/domain/analysis';
import type { AnalysisJob, AnalysisMetadataResponse } from '@/types/domain/analysis';

// `measure` and the stage thresholds have their own tests in
// `run-context.test.ts`. What matters here is that this card uses them to render
// the right thing, and that it never invents a figure to fill a gap.

// ======================================================================
// formatElapsed
// ======================================================================

describe('formatElapsed', () => {
  it.each([
    [0, '0s'],
    [9, '9s'],
    [59, '59s'],
    [60, '1m 0s'],
    [95, '1m 35s'],
    [3599, '59m 59s'],
    [3600, '1h 0m'],
    [3900, '1h 5m'],
  ])('formats %i seconds as %s', (seconds, expected) => {
    expect(formatElapsed(seconds)).toBe(expected);
  });
});

// ======================================================================
// Builders
// ======================================================================

function job(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    job_id: 'abcdef12-3456-7890-abcd-ef1234567890',
    repo_id: 'repo-1',
    workspace_id: 'ws-98765432-1111-2222-3333-444444444444',
    status: JobStatus.PARSING,
    repo_url: 'https://github.com/acme/widget',
    branch: 'feature/x',
    progress_pct: 30,
    progress_message: 'Parsing files...',
    total_findings: 0,
    total_files: null,
    total_lines: null,
    overall_score: null,
    blocked_by: [],
    engine_statuses: {},
    error_message: null,
    created_at: '2026-01-01T00:00:00Z',
    started_at: null,
    completed_at: null,
    languages_detected: null,
    language_breakdown: null,
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

// ======================================================================
// Before anything has been measured
// ======================================================================

describe('a queued job shows no invented figures', () => {
  it('shows a placeholder for every count', () => {
    render(<ProjectContextCard job={job({ progress_pct: 0 })} metadata={null} />);

    for (const label of [
      'Files',
      'Lines',
      'Classes',
      'Functions',
      'Endpoints',
      'Frameworks',
    ]) {
      expect(screen.getByLabelText(`${label} not measured yet`)).toBeInTheDocument();
    }
  });

  it('renders no zero anywhere', () => {
    render(<ProjectContextCard job={job({ progress_pct: 0 })} metadata={null} />);

    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('says the run has not started rather than showing a duration', () => {
    render(<ProjectContextCard job={job({ progress_pct: 0 })} metadata={null} />);

    // Two rows report it: Started and Elapsed.
    expect(screen.getAllByText('Once the run starts')).toHaveLength(2);
  });

  it('names the stage that will produce the counts', () => {
    render(<ProjectContextCard job={job({ progress_pct: 5 })} metadata={null} />);

    // "Not yet" is answered with what is coming, not a dash.
    expect(screen.getByText('Waiting for the clone')).toBeInTheDocument();
  });

  it('shows the run identity the job already has', () => {
    render(<ProjectContextCard job={job({ progress_pct: 0 })} metadata={null} />);

    expect(screen.getByText('acme/widget')).toBeInTheDocument();
    expect(screen.getByText('feature/x')).toBeInTheDocument();
    expect(screen.getByText('abcdef12')).toBeInTheDocument();
    // First eight characters, matching how the workspace id is shown elsewhere.
    expect(screen.getByText('ws-98765')).toBeInTheDocument();
  });

  it('shows the queued status in words', () => {
    render(<ProjectContextCard job={job({ status: JobStatus.QUEUED })} metadata={null} />);

    expect(screen.getByText('Queued')).toBeInTheDocument();
  });

  it('falls back to the raw status for a status it has no word for', () => {
    render(
      <ProjectContextCard
        job={job({ status: 'brand_new' as JobStatus })}
        metadata={null}
      />,
    );

    expect(screen.getByText('brand_new')).toBeInTheDocument();
  });

  it('renders the whole-card skeleton when the job is still loading', () => {
    const { container } = render(<ProjectContextCard job={null} isLoading />);

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(10);
    expect(screen.queryByText('Repository')).not.toBeInTheDocument();
  });

  it('skeletons when loading even if a job was passed', () => {
    // The loading state means the job on screen is the previous one, not this
    // page's, so showing its figures would be showing the wrong repository.
    render(<ProjectContextCard job={job({ branch: 'stale' })} isLoading />);

    expect(screen.queryByText('stale')).not.toBeInTheDocument();
  });
});

// ======================================================================
// Mid-run: what each stage has genuinely established
// ======================================================================

describe('a parsing job shows what has actually been measured', () => {
  it('shows the counts clone established', () => {
    render(
      <ProjectContextCard
        job={job({ total_files: 120, total_lines: 8400 })}
        metadata={null}
      />,
    );

    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('8,400')).toBeInTheDocument();
  });

  it('shows the entity counts parse has established', () => {
    render(
      <ProjectContextCard
        job={job({ progress_pct: 45 })}
        metadata={meta()}
      />,
    );

    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('210')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('marks a mid-parse count as still being recounted', () => {
    render(<ProjectContextCard job={job({ progress_pct: 45 })} metadata={meta()} />);

    expect(
      screen.getByTitle('Classes, still being recounted'),
    ).toBeInTheDocument();
  });

  it('marks a settled count as measured', () => {
    render(<ProjectContextCard job={job({ progress_pct: 80 })} metadata={meta()} />);

    expect(screen.getByTitle('Classes, measured')).toBeInTheDocument();
  });

  it('still shows placeholders for counts parse has not reached', () => {
    render(
      <ProjectContextCard
        job={job({ total_files: 120, total_lines: 8400 })}
        metadata={null}
      />,
    );

    expect(screen.getByLabelText('Classes not measured yet')).toBeInTheDocument();
  });

  it('lists the languages clone detected', () => {
    render(
      <ProjectContextCard
        job={job({ languages_detected: ['Python', 'Go'] })}
        metadata={null}
      />,
    );

    expect(screen.getByText('Python, Go')).toBeInTheDocument();
  });

  it('says none were detected when clone ran and found none', () => {
    // Different from "not measured": this is a completed measurement with an
    // empty result, and it must not render as a placeholder.
    render(
      <ProjectContextCard job={job({ languages_detected: [] })} metadata={null} />,
    );

    expect(screen.getByText('None detected')).toBeInTheDocument();
    expect(screen.queryByText('Waiting for the clone')).not.toBeInTheDocument();
  });

  it('counts frameworks rather than pretending to render a set', () => {
    render(<ProjectContextCard job={job({ progress_pct: 45 })} metadata={meta()} />);

    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows a zero framework count when detection found none', () => {
    render(
      <ProjectContextCard
        job={job({ progress_pct: 45 })}
        metadata={meta({ frameworks: [] })}
      />,
    );

    expect(screen.getByText('0')).toBeInTheDocument();
  });
});

// ======================================================================
// Elapsed time
// ======================================================================

describe('elapsed time', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('counts up while the run is in flight', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    const startedAt = new Date(Date.now() - 65_000).toISOString();
    render(
      <ProjectContextCard
        job={job({ status: JobStatus.PARSING, started_at: startedAt })}
        metadata={null}
      />,
    );

    expect(screen.getByText('1m 5s')).toBeInTheDocument();
  });

  it('ticks as time passes', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    const startedAt = new Date(Date.now() - 10_000).toISOString();
    render(
      <ProjectContextCard
        job={job({ status: JobStatus.PARSING, started_at: startedAt })}
        metadata={null}
      />,
    );

    expect(screen.getByText('10s')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(5_000);
    });

    expect(screen.getByText('15s')).toBeInTheDocument();
  });

  it('reports a completed run the distance between its two timestamps', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T12:00:00Z'));

    // Ended two minutes in, but the page has been open for twelve hours. The
    // run's real duration is two minutes, and reporting twelve hours would be
    // claiming it took all that.
    render(
      <ProjectContextCard
        job={job({
          status: JobStatus.COMPLETED,
          started_at: '2026-01-01T00:00:00Z',
          completed_at: '2026-01-01T00:02:00Z',
        })}
        metadata={meta()}
      />,
    );

    expect(screen.getByText('2m 0s')).toBeInTheDocument();
  });

  it('stops counting a completed run', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:02:00Z'));

    render(
      <ProjectContextCard
        job={job({
          status: JobStatus.COMPLETED,
          started_at: '2026-01-01T00:00:00Z',
          completed_at: '2026-01-01T00:02:00Z',
        })}
        metadata={meta()}
      />,
    );

    act(() => {
      vi.advanceTimersByTime(600_000);
    });

    expect(screen.getByText('2m 0s')).toBeInTheDocument();
  });

  it('stops counting a failed run and reports how long it got', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T06:00:00Z'));

    // The case a live counter gets wrong most visibly: a failed run measured
    // against `now` keeps climbing for as long as the page is open.
    render(
      <ProjectContextCard
        job={job({
          status: JobStatus.FAILED,
          started_at: '2026-01-01T00:00:00Z',
          completed_at: '2026-01-01T00:00:42Z',
        })}
        metadata={null}
      />,
    );

    expect(screen.getByText('42s')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3_600_000);
    });

    expect(screen.getByText('42s')).toBeInTheDocument();
  });

  it('will not report a negative duration when the browser clock lags', () => {
    // A browser clock behind the service's would otherwise show a negative
    // elapsed time, which reads as a bug rather than as clock skew.
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    render(
      <ProjectContextCard
        job={job({
          status: JobStatus.PARSING,
          started_at: '2026-01-01T01:00:00Z',
        })}
        metadata={null}
      />,
    );

    expect(screen.getByText('Measuring')).toBeInTheDocument();
  });

  it('falls back to live counting when a finished run recorded no end time', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:01:00Z'));

    render(
      <ProjectContextCard
        job={job({
          status: JobStatus.COMPLETED,
          started_at: '2026-01-01T00:00:00Z',
          completed_at: null,
        })}
        metadata={meta()}
      />,
    );

    expect(screen.getByText('1m 0s')).toBeInTheDocument();
  });

  it('renders the panel rather than crashing on an unparseable start time', () => {
    // `formatRelativeTime` falls through to `Intl.DateTimeFormat.format` when the
    // date will not parse, and that throws `RangeError` on an invalid Date. A
    // malformed timestamp from the API would take down the whole sidebar, so the
    // card treats it as no timestamp at all.
    expect(() =>
      render(
        <ProjectContextCard
          job={job({ started_at: 'not-a-date' })}
          metadata={null}
        />,
      ),
    ).not.toThrow();

    expect(screen.getAllByText('Once the run starts')).toHaveLength(2);
  });

  
});

// ======================================================================
// Status
// ======================================================================

describe('the status row', () => {
  it('names every in-flight stage', () => {
    const cases: Array<[JobStatus, string]> = [
      [JobStatus.QUEUED, 'Queued'],
      [JobStatus.CLONING, 'Cloning'],
      [JobStatus.PARSING, 'Parsing'],
      [JobStatus.RULES, 'Rules'],
      [JobStatus.DEAD_CODE, 'Dead code'],
      [JobStatus.ERRORS, 'Errors'],
      [JobStatus.PERF, 'Performance'],
      [JobStatus.SIMULATION, 'Simulation'],
      [JobStatus.SCORING, 'Scoring'],
      [JobStatus.GUIDE_GEN, 'Writing guide'],
      [JobStatus.COMPLETED, 'Complete'],
      [JobStatus.FAILED, 'Failed'],
    ];

    for (const [status, label] of cases) {
      const { unmount } = render(
        <ProjectContextCard job={job({ status })} metadata={null} />,
      );
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it('marks a failed run in the danger colour', () => {
    const { container } = render(
      <ProjectContextCard job={job({ status: JobStatus.FAILED })} metadata={null} />,
    );

    expect(container.querySelector('.text-red-400')).not.toBeNull();
  });

  it('does not mark a running job as failed', () => {
    const { container } = render(
      <ProjectContextCard
        job={job({ status: JobStatus.PARSING })}
        metadata={null}
      />,
    );

    expect(container.querySelector('.text-red-400')).toBeNull();
  });
});

// ======================================================================
// Repository naming
// ======================================================================

describe('repository naming', () => {
  it('shows owner/repo for a github url', () => {
    render(
      <ProjectContextCard
        job={job({ repo_url: 'https://github.com/acme/widget' })}
        metadata={null}
      />,
    );

    expect(screen.getByText('acme/widget')).toBeInTheDocument();
  });

  it('drops a trailing .git', () => {
    render(
      <ProjectContextCard
        job={job({ repo_url: 'https://github.com/acme/widget.git' })}
        metadata={null}
      />,
    );

    expect(screen.getByText('acme/widget')).toBeInTheDocument();
  });

  it('keeps a self-hosted url rather than discarding it', () => {
    render(
      <ProjectContextCard
        job={job({ repo_url: 'https://git.internal.acme/team/widget.git' })}
        metadata={null}
      />,
    );

    expect(screen.getByText('git.internal.acme/team/widget')).toBeInTheDocument();
  });

  it('keeps an ssh url', () => {
    render(
      <ProjectContextCard
        job={job({ repo_url: 'git@github.com:acme/widget.git' })}
        metadata={null}
      />,
    );

    expect(screen.getByText('git@github.com:acme/widget')).toBeInTheDocument();
  });

  it('names the missing url rather than showing nothing', () => {
    render(<ProjectContextCard job={job({ repo_url: '' })} metadata={null} />);

    // Repository and Branch both name the clone as what is coming.
    expect(screen.getAllByText('Waiting for the clone').length).toBeGreaterThanOrEqual(2);
  });

  it('names an unrecorded branch rather than defaulting to main', () => {
    // The start request defaults the branch to main, but a job row that never
    // recorded one is missing it, not on main.
    render(<ProjectContextCard job={job({ branch: '' })} metadata={null} />);

    expect(screen.getAllByText('Waiting for the clone').length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText('main')).not.toBeInTheDocument();
  });
});