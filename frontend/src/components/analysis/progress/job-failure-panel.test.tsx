import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JobFailurePanel } from './JobFailurePanel';
import { JobStatus } from '@/types/domain/analysis';
import type { AnalysisJob, EngineStatusItem } from '@/types/domain/analysis';

/**
 * The panel answers the questions someone opens a failed job to ask: what broke,
 * how far it got, and what still worked.
 *
 * The block it replaces rendered `job.error_message || 'Unknown error'` -- a
 * missing reason presented as a reason -- and a grid of engine cards that could
 * not name a single one of them. Most of what follows is about not inventing an
 * answer where there isn't one.
 */

afterEach(() => {
  vi.useRealTimers();
});

function job(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    job_id: 'job-1',
    repo_id: 'repo-1',
    workspace_id: 'ws-1',
    status: JobStatus.FAILED,
    repo_url: 'https://github.com/acme/app',
    branch: 'main',
    progress_pct: 62,
    progress_message: 'Failed at stage: rules',
    total_findings: 0,
    total_files: 480,
    total_lines: 12000,
    overall_score: null,
    blocked_by: [],
    engine_statuses: {},
    error_message: 'rules failed: SemgrepError - exit code 2',
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:00Z',
    completed_at: '2026-01-01T00:02:14Z',
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
    score: null,
    error: null,
    ...overrides,
  };
}

/** Two finished cleanly, one failed, six that never started. */
const PART_WAY: EngineStatusItem[] = [
  item({ key: 'churn', name: 'Churn', status: 'completed', duration: '2s' }),
  item({
    key: 'security',
    name: 'Security',
    status: 'failed',
    duration: '31s',
    error: 'rules: SemgrepError - exit code 2',
  }),
  item({ key: 'reliability', name: 'Reliability', status: 'completed', duration: '6s' }),
  ...['maintainability', 'devops', 'dead_code', 'errors', 'perf', 'simulation'].map(key =>
    item({ key, name: key, status: 'pending', duration: null }),
  ),
];

describe('the failure reason', () => {
  it('shows what the service recorded', () => {
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    expect(
      screen.getByText('rules failed: SemgrepError - exit code 2'),
    ).not.toBeNull();
  });

  it('names the stage, because the message alone does not have to', () => {
    // The stage is the difference between "exit code 2" and "the security scan
    // exited 2". `describe_failure` guarantees it is in the message; this is the
    // UI agreeing to carry it rather than rendering the raw exception separately
    // and hoping the two match.
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    expect(screen.getByText(/rules failed/)).not.toBeNull();
  });

  it('says no reason was recorded rather than inventing one', () => {
    // The old block rendered "Unknown error", which claims an error exists and
    // could not be read. Two different things, and only one of them is true --
    // and neither is knowable from a null column. What is knowable is that the
    // record is empty.
    render(<JobFailurePanel job={job({ error_message: null })} items={PART_WAY} />);

    expect(
      screen.getByText('No failure reason was recorded for this run.'),
    ).not.toBeNull();
    expect(screen.queryByText(/Unknown error/)).toBeNull();
  });

  it('treats an empty string as no reason', () => {
    render(<JobFailurePanel job={job({ error_message: '' })} items={PART_WAY} />);

    expect(
      screen.getByText('No failure reason was recorded for this run.'),
    ).not.toBeNull();
  });

  it('breaks a long message instead of letting it run off the panel', () => {
    const long = `rules failed: ${'detail '.repeat(80)}`;
    const { container } = render(
      <JobFailurePanel job={job({ error_message: long })} items={PART_WAY} />,
    );

    // The message is bounded to 400 characters server-side, which is still longer
    // than fits on a phone-width panel.
    expect(container.querySelector('.break-words')).not.toBeNull();
  });
});

describe('where the run got to', () => {
  it('shows the percentage the run actually reached', () => {
    // The bar is not rewound on failure -- that was fixed so a job that died at
    // 90% would not read as 0%. Rendering it here is what makes "where did it
    // stop" answerable.
    render(<JobFailurePanel job={job({ progress_pct: 62 })} items={PART_WAY} />);

    expect(screen.getByText('62%')).not.toBeNull();
  });

  it('clamps a percentage outside 0-100 rather than overflowing the bar', () => {
    render(<JobFailurePanel job={job({ progress_pct: 140 })} items={PART_WAY} />);

    expect(screen.getByText('100%')).not.toBeNull();
  });

  it('shows the failure stage line the service recorded', () => {
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    expect(screen.getByText('Failed at stage: rules')).not.toBeNull();
  });
});

describe('what still worked', () => {
  // The summary is asserted as a whole line rather than part by part. It is
  // rendered as one string, and it only reads correctly in the order it is
  // assembled -- "3 of 9 finished · 6 never started" says something different
  // from "6 never started · 3 of 9 finished", and a matcher on a fragment would
  // not notice.
  //
  // `completed_at` is dropped for this whole block so the line is only about the
  // engine counts. It is measured separately below, and the default fixture is
  // realistic -- a failed job now records when it stopped.

  it('counts an engine that failed as finished work', () => {
    // A failed engine did run. Leaving it out of the count would understate how
    // much of the run happened -- and it would be the wrong direction, making a
    // run that got most of the way through look like it stopped at the start.
    render(<JobFailurePanel job={job({ completed_at: null })} items={PART_WAY} />);

    expect(
      screen.getByText('3 of 9 engines finished · 1 failed · 6 never started'),
    ).not.toBeNull();
  });

  it('omits every part that is zero', () => {
    // "0 failed" on a run where nothing failed is noise. And the panel runs for
    // failures with no engine failure at all -- a clone failure, say -- where a
    // "0 failed" clause would be actively wrong-looking. Turning the one failed
    // row into a waiting one also drops it out of the finished count, which is
    // why this line says 2 rather than 3.
    const noEngineFailure = PART_WAY.map(i =>
      i.status === 'failed' ? { ...i, status: 'pending' as const, error: null } : i,
    );

    render(
      <JobFailurePanel job={job({ completed_at: null })} items={noEngineFailure} />,
    );

    expect(screen.getByText('2 of 9 engines finished · 7 never started')).not.toBeNull();
  });

  it('reports an engine the service could not describe separately from one that never ran', () => {
    // "Unavailable" means the status is unknown, not that the engine sat in the
    // queue. Folding the two together would let "never started" mean something
    // it does not.
    const withUnknown = [
      ...PART_WAY.slice(0, 5),
      ...PART_WAY.slice(5, 8).map(i => ({ ...i, status: 'unavailable' as const })),
      item({ key: 'last', name: 'Last', status: 'unavailable', duration: null }),
    ];

    render(<JobFailurePanel job={job({ completed_at: null })} items={withUnknown} />);

    expect(
      screen.getByText(
        '3 of 9 engines finished · 1 failed · 2 never started · 4 not reported',
      ),
    ).not.toBeNull();
  });

  it('omits the whole summary when the run reported no engines', () => {
    // "0 of 0 engines finished" is a fact about nothing. The separate
    // no-engines line already says what happened.
    render(<JobFailurePanel job={job()} items={[]} />);

    expect(screen.queryByText(/engines finished/)).toBeNull();
    expect(screen.getByText('No engines reported for this run.')).not.toBeNull();
  });

  it('counts a skipped engine as finished', () => {
    // Skipped means the pipeline decided, not that it ran. Either way it is no
    // longer waiting, so it belongs in the settled count rather than making the
    // run look cut short.
    const withSkip = PART_WAY.map(i =>
      i.status === 'pending' && i.key === 'perf'
        ? { ...i, status: 'skipped' as const }
        : i,
    );

    render(<JobFailurePanel job={job({ completed_at: null })} items={withSkip} />);

    expect(
      screen.getByText('4 of 9 engines finished · 1 failed · 5 never started'),
    ).not.toBeNull();
  });
});

describe('how long it ran', () => {
  it('measures between the two instants the run recorded', () => {
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    expect(
      screen.getByText(
        '3 of 9 engines finished · 1 failed · 6 never started · ran for 2m 14s',
      ),
    ).not.toBeNull();
  });

  it('shows no duration when the run never recorded an end', () => {
    // `completed_at` is written for failed jobs from this branch onwards. A row
    // written before that has none, and the panel must not fall back to measuring
    // against `now` -- that figure would grow for as long as the page is open.
    render(<JobFailurePanel job={job({ completed_at: null })} items={PART_WAY} />);

    expect(
      screen.getByText('3 of 9 engines finished · 1 failed · 6 never started'),
    ).not.toBeNull();
  });

  it('shows no duration when there is no start either', () => {
    render(
      <JobFailurePanel
        job={job({ started_at: null, completed_at: null })}
        items={PART_WAY}
      />,
    );

    expect(screen.getByText(/engines finished/)).not.toBeNull();
    expect(screen.queryByText(/ran for/)).toBeNull();
  });

  it('shows no duration for an unparseable timestamp', () => {
    render(<JobFailurePanel job={job({ started_at: 'whenever' })} items={PART_WAY} />);

    // `Intl.DateTimeFormat.format` throws `RangeError` on an invalid `Date`, and
    // `usableTimestamp` is what stops that taking the panel down with it.
    expect(screen.getByText(/engines finished/)).not.toBeNull();
    expect(screen.queryByText(/ran for/)).toBeNull();
  });
});

describe('the per-engine rows', () => {
  it('shows the reason the failed engine recorded', () => {
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    // The service's own message for that engine. The old card said "Engine
    // encountered errors during scan" for all five of its hardcoded engines, so
    // this is the first time a reader could learn which engine failed and why.
    expect(screen.getByText('rules: SemgrepError - exit code 2')).not.toBeNull();
  });

  it('marks the failed row and the ones that never ran distinctly', () => {
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    expect(screen.getByText('Failed')).not.toBeNull();
    expect(screen.getAllByText('Waiting')).toHaveLength(6);
    expect(screen.getAllByText('Completed')).toHaveLength(2);
  });

  it('gives no row a ticking timer, because a failed run has no clock running', () => {
    // A row the service still records as `running` is inconsistent with a failed
    // job, and the pipeline never produces one. The panel passes no start times,
    // so the step cannot count -- it renders "Measuring" and stops, which is
    // visibly wrong and inert. Relabelling the state to make it look right would
    // be inventing a status the service did not report.
    render(
      <JobFailurePanel
        job={job()}
        items={[item({ key: 'security', status: 'running', duration: null })]}
      />,
    );

    expect(screen.getByText('Measuring')).not.toBeNull();
  });

  it('shows no duration for an engine that never ran', () => {
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    // "0s" would claim the engine ran and finished instantly, which is exactly
    // what a duration that was never recorded looks like.
    const rows = screen.getAllByRole('listitem');
    const waitingRow = rows.find(r => r.textContent?.includes('Waiting'));
    expect(waitingRow?.textContent).not.toMatch(/\d+s/);
  });
});

describe('a job that failed before any engine ran', () => {
  it('still names the stage and the reason', () => {
    render(
      <JobFailurePanel
        job={job({
          progress_pct: 5,
          progress_message: 'Failed at stage: clone',
          error_message: 'clone failed: RepositoryNotFoundError - 404',
        })}
        items={PART_WAY.map(i => ({ ...i, status: 'pending' as const, error: null }))}
      />,
    );

    expect(screen.getByText('clone failed: RepositoryNotFoundError - 404')).not.toBeNull();
    expect(screen.getByText(/0 of 9 engines finished/)).not.toBeNull();
  });
});

describe('the retry action', () => {
  it('is absent when no handler was given', () => {
    // The panel is presentational. A caller that does not supply the action gets
    // a panel that reports the failure and offers nothing, rather than a dead
    // button that quietly does nothing when pressed.
    render(<JobFailurePanel job={job()} items={PART_WAY} />);

    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.queryByText(/Retry the whole analysis/)).toBeNull();
  });

  it('calls the handler when pressed', async () => {
    const onRetry = vi.fn();
    render(<JobFailurePanel job={job()} items={PART_WAY} onRetry={onRetry} />);

    await userEvent.click(screen.getByRole('button', { name: /Retry the whole analysis/ }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('says the whole analysis runs again, not just the engine that failed', () => {
    // There is no per-engine retry, and a panel showing six engines as "never
    // started" is exactly the situation where a reader would assume one. The
    // label has to rule that out rather than leaving it to be discovered.
    render(<JobFailurePanel job={job()} items={PART_WAY} onRetry={vi.fn()} />);

    expect(screen.getByRole('button', { name: /whole analysis/ })).not.toBeNull();
    expect(screen.getByText(/Every engine runs again from the start/)).not.toBeNull();
  });

  it('says the failed run is kept, because a retry creates a second job', () => {
    // Nothing is overwritten -- the retry is a new job row. Worth saying, because
    // "retry" reads like it might replace what is on screen.
    render(<JobFailurePanel job={job()} items={PART_WAY} onRetry={vi.fn()} />);

    expect(screen.getByText(/This run is kept/)).not.toBeNull();
  });

  it('is disabled and relabelled while the retry is being accepted', async () => {
    // The label used to read "Reanalyzing..." from the header button, which
    // describes a run that is under way. What is in flight here is the request
    // that starts one.
    const onRetry = vi.fn();
    render(
      <JobFailurePanel job={job()} items={PART_WAY} onRetry={onRetry} isRetrying />,
    );

    const button = screen.getByRole('button', { name: /Starting retry/ });
    expect((button as HTMLButtonElement).disabled).toBe(true);

    // Disabled must actually prevent the call. The handler's own guard is the
    // real protection, but a button that fires while it looks disabled is its
    // own small lie.
    await userEvent.click(button);
    expect(onRetry).not.toHaveBeenCalled();
  });

  it('sits above the engine list, so the action is not below nine rows', () => {
    render(<JobFailurePanel job={job()} items={PART_WAY} onRetry={vi.fn()} />);

    // The accounting is what justifies retrying, so the button belongs next to
    // it. Asserting DOM order rather than pixel position: this is a reading
    // order question, and reading order is what a screen reader follows.
    const summary = screen.getByText(/engines finished/);
    const button = screen.getByRole('button', { name: /Retry/ });

    expect(summary.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});