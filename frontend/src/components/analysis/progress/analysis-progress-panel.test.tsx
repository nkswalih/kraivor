import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AnalysisProgressPanel } from './AnalysisProgressPanel';
import { JobStatus } from '@/types/domain/analysis';
import type { AnalysisJob, EngineStatusMap, EngineStatusItem } from '@/types/domain/analysis';

/**
 * The panel answers three questions for someone watching a run: how far along it
 * is, what is happening this second, and where every engine stands. The tests
 * below pin each of those, plus the distinction the panel exists to preserve --
 * a figure it does not have is reported as missing rather than filled in.
 */

afterEach(() => {
  vi.useRealTimers();
});

function job(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    job_id: 'job-1',
    repo_id: 'repo-1',
    workspace_id: 'ws-1',
    status: JobStatus.PARSING,
    repo_url: 'https://github.com/acme/app',
    branch: 'main',
    progress_pct: 45,
    progress_message: 'Scanning 120 of 480 files',
    total_findings: 0,
    total_files: 480,
    total_lines: 12000,
    overall_score: null,
    blocked_by: [],
    engine_statuses: {},
    error_message: null,
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:00Z',
    completed_at: null,
    languages_detected: null,
    language_breakdown: null,
    ...overrides,
  };
}

function item(overrides: Partial<EngineStatusItem> = {}): EngineStatusItem {
  return {
    name: 'Security',
    key: 'security',
    description: '',
    status: 'completed',
    duration: '4s',
    score: 91,
    error: null,
    ...overrides,
  };
}

function statuses(entries: Record<string, Partial<EngineStatusMap[string]>>): EngineStatusMap {
  const map: EngineStatusMap = {};
  for (const [key, value] of Object.entries(entries)) {
    map[key] = value as EngineStatusMap[string];
  }
  return map;
}

const done = item({ key: 'churn', name: 'Churn', status: 'completed', duration: '3s', score: 88 });
const running = item({
  key: 'security',
  name: 'Security',
  status: 'running',
  duration: null,
  score: null,
});
const waiting = item({
  key: 'reliability',
  name: 'Reliability',
  status: 'pending',
  duration: null,
  score: null,
});

// ======================================================================
// The bar
// ======================================================================

describe('AnalysisProgressPanel progress bar', () => {
  it('shows the percentage the service reported', () => {
    const { container } = render(
      <AnalysisProgressPanel
        job={job({ progress_pct: 45 })}
        engineStatuses={{}}
        items={[done]}
      />,
    );

    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(container.querySelector<HTMLElement>('.h-full')?.style.width).toBe('45%');
  });

  it('shows the message twice, once on the bar and once as the current line', () => {
    // Once because the bar labels itself, once because the line under it is the
    // live statement of what is happening right now.
    render(
      <AnalysisProgressPanel
        job={job({ progress_message: 'Scanning 120 of 480 files' })}
        engineStatuses={{}}
        items={[done]}
      />,
    );

    expect(screen.getAllByText('Scanning 120 of 480 files')).toHaveLength(2);
  });

  it('says the run is in progress when the service has sent no message', () => {
    render(
      <AnalysisProgressPanel
        job={job({ progress_message: '' })}
        engineStatuses={{}}
        items={[done]}
      />,
    );

    // Once, not twice. `ProgressBar` drops its label row when there is no
    // message to label, so the fallback belongs only to the live line -- which is
    // where it answers the question the bar's label would have answered.
    expect(screen.getAllByText('Analysis in progress')).toHaveLength(1);
  });
});

// ======================================================================
// The summary line
// ======================================================================

describe('AnalysisProgressPanel summary line', () => {
  it('counts the engines that have finished', () => {
    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={{}}
        items={[done, running, waiting]}
      />,
    );

    expect(screen.getByText(/1 of 3 engines/)).toBeInTheDocument();
  });

  it('counts skipped engines as finished, since they will not run', () => {
    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={{}}
        items={[
          done,
          running,
          item({ key: 'simulation', name: 'Simulation', status: 'skipped', duration: null, score: null }),
        ]}
      />,
    );

    expect(screen.getByText(/2 of 3 engines/)).toBeInTheDocument();
  });

  it('counts a failed engine as finished, so the count can reach the total', () => {
    // A failed engine is done, and the pipeline moves past it. Counting only
    // successes would leave the panel permanently short of the total on any run
    // that hit a failure.
    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={{}}
        items={[
          item({ key: 'security', name: 'Security', status: 'failed', duration: null, score: null, error: 'boom' }),
        ]}
      />,
    );

    expect(screen.getByText(/1 of 1 engines/)).toBeInTheDocument();
  });

  it('counts a queued run as none finished', () => {
    render(
      <AnalysisProgressPanel
        job={job({ started_at: null })}
        engineStatuses={{}}
        items={[waiting]}
      />,
    );

    expect(screen.getByText(/0 of 1 engines/)).toBeInTheDocument();
  });

  it('appends the elapsed time while the run is in flight', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:02:00Z'));

    render(
      <AnalysisProgressPanel
        job={job({ started_at: '2026-01-01T00:00:00Z' })}
        engineStatuses={{}}
        items={[done, running]}
      />,
    );

    expect(screen.getByText(/1 of 2 engines · 2m 0s/)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(30_000);
    });

    expect(screen.getByText(/1 of 2 engines · 2m 30s/)).toBeInTheDocument();
  });

  it('counts up only while the run is in flight', () => {
    // The panel is only mounted for running jobs, but it must not run a
    // once-a-second interval on a finished run if it ever is mounted for one --
    // on a failed run the count would never stop.
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:05:00Z'));

    render(
      <AnalysisProgressPanel
        job={job({ status: JobStatus.FAILED, started_at: '2026-01-01T00:00:00Z' })}
        engineStatuses={{}}
        items={[done]}
      />,
    );

    expect(screen.getByText('1 of 1 engines')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(600_000);
    });

    expect(screen.getByText('1 of 1 engines')).toBeInTheDocument();
  });

  it('omits the elapsed time rather than inventing one when there is no start', () => {
    render(
      <AnalysisProgressPanel
        job={job({ started_at: null })}
        engineStatuses={{}}
        items={[done, running]}
      />,
    );

    // No start time means no measured duration. "0s" would claim the run had been
    // going for zero seconds, and appending a bare separator would read as a
    // formatting glitch rather than as a missing measurement.
    expect(screen.getByText('1 of 2 engines')).toBeInTheDocument();
  });

  it('omits the elapsed time when the clock is behind the start', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    render(
      <AnalysisProgressPanel
        job={job({ started_at: '2026-01-01T01:00:00Z' })}
        engineStatuses={{}}
        items={[done]}
      />,
    );

    expect(screen.getByText('1 of 1 engines')).toBeInTheDocument();
  });

  it('reports a settled run as the window it recorded, not the time since it began', () => {
    vi.useFakeTimers();
    // Ten minutes after it finished.
    vi.setSystemTime(new Date('2026-01-01T00:10:00Z'));

    render(
      <AnalysisProgressPanel
        job={job({
          status: JobStatus.COMPLETED,
          started_at: '2026-01-01T00:00:00Z',
          completed_at: '2026-01-01T00:02:00Z',
        })}
        engineStatuses={{}}
        items={[done]}
      />,
    );

    // Two minutes, from the two instants the service wrote. Measuring to `now`
    // would report this run as still taking ten minutes, and would grow for as
    // long as the page stayed open.
    expect(screen.getByText('1 of 1 engines · 2m 0s')).toBeInTheDocument();
  });
});

// ======================================================================
// Failures partway through
// ======================================================================

describe('AnalysisProgressPanel partial failure', () => {
  it('says one engine failed and the run continues', () => {
    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={{}}
        items={[
          done,
          item({ key: 'security', name: 'Security', status: 'failed', duration: null, score: null, error: 'boom' }),
          waiting,
        ]}
      />,
    );

    expect(
      screen.getByText(/1 engine failed — the run continues without it/),
    ).toBeInTheDocument();
  });

  it('pluralises and names the others when more than one fails', () => {
    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={{}}
        items={[
          item({ key: 'a', name: 'A', status: 'failed', duration: null, score: null, error: 'x' }),
          item({ key: 'b', name: 'B', status: 'failed', duration: null, score: null, error: 'y' }),
        ]}
      />,
    );

    expect(
      screen.getByText(/2 engines failed — the run continues without them/),
    ).toBeInTheDocument();
  });

  it('says nothing about failure when none failed', () => {
    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={{}}
        items={[done, running]}
      />,
    );

    expect(screen.queryByText(/failed — the run continues/)).not.toBeInTheDocument();
  });
});

// ======================================================================
// The step list
// ======================================================================

describe('AnalysisProgressPanel step list', () => {
  it('renders every engine, in the order given', () => {
    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={{}}
        items={[done, running, waiting]}
      />,
    );

    const labels = screen
      .getAllByRole('listitem')
      .map((row) => row.querySelector('span[title]')?.textContent);

    expect(labels).toEqual(['Churn', 'Security', 'Reliability']);
  });

  it('gives the running engine the start time the status map records', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:20Z'));

    render(
      <AnalysisProgressPanel
        job={job()}
        engineStatuses={statuses({
          security: {
            status: 'running',
            started_at: '2026-01-01T00:00:00Z',
            ended_at: null,
            error: '',
          },
        })}
        items={[done, running]}
      />,
    );

    // The run and this engine both started at 00:00:00, so the elapsed figure on
    // the summary line is 20s too -- what is being checked here is that the step
    // is counting at all, which it cannot do without the map.
    expect(screen.getByText('20s')).toBeInTheDocument();
  });

  it('reads a bare-string engine state without crashing', () => {
    // Jobs analysed before per-engine timings carry a bare status string. The
    // panel must render those too, and must not read `started_at` off a string.
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    expect(() =>
      render(
        <AnalysisProgressPanel
          job={job()}
          engineStatuses={{ security: 'running' }}
          items={[running]}
        />,
      ),
    ).not.toThrow();

    // No start time behind a bare string, so no live count -- and no zero either.
    expect(screen.getByText('Measuring')).toBeInTheDocument();
  });

  it('says so when the job reports no engines at all', () => {
    render(
      <AnalysisProgressPanel job={job()} engineStatuses={{}} items={[]} />,
    );

    // An empty list with no explanation reads as a rendering failure. An empty
    // list that says the service reported none is a fact about the run.
    expect(screen.getByText('No engines reported for this run.')).toBeInTheDocument();
  });
});
