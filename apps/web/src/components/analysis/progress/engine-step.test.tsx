import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { EngineStep } from './EngineStep';
import type { EngineStatusItem } from '@/types/domain/analysis';

/**
 * A step is the running view of one engine. The properties worth pinning are the
 * ones the old engine card got wrong: every state the service can report has its
 * own rendering, a running engine counts its own time, a queued one claims no
 * time at all, and a failure says why.
 */

afterEach(() => {
  vi.useRealTimers();
});

function item(overrides: Partial<EngineStatusItem> = {}): EngineStatusItem {
  return {
    name: 'Security',
    key: 'security',
    description: 'Injection, auth and secret-handling checks',
    status: 'completed',
    duration: '4s',
    score: 91,
    error: null,
    ...overrides,
  };
}

// ======================================================================
// States
// ======================================================================

describe('EngineStep states', () => {
  it.each([
    ['completed', 'Completed'],
    ['running', 'Running'],
    ['failed', 'Failed'],
    ['skipped', 'Skipped'],
    ['pending', 'Waiting'],
    ['unavailable', 'Unavailable'],
  ] as const)('labels a %s engine %s', (status, label) => {
    render(<EngineStep item={item({ status })} />);

    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('marks only the running step as the current one', () => {
    const { rerender } = render(<EngineStep item={item({ status: 'running' })} />);

    expect(screen.getByRole('listitem')).toHaveAttribute('aria-current', 'step');

    rerender(<EngineStep item={item({ status: 'completed' })} />);

    expect(screen.getByRole('listitem')).not.toHaveAttribute('aria-current');
  });

  it('calls a queued engine Waiting rather than Pending', () => {
    // "Pending" reads as something in hand that has not been decided.
    // "Waiting" says the same thing without implying work is queued behind a
    // decision, which is not what a pipeline stage gap is.
    render(<EngineStep item={item({ status: 'pending' })} />);

    expect(screen.getByText('Waiting')).toBeInTheDocument();
    expect(screen.queryByText('Pending')).not.toBeInTheDocument();
  });

  it('falls back to Waiting for a state it has no style for', () => {
    // The service can add a state before the UI knows it. An unstyled state
    // rendering as blank would be worse than rendering as waiting.
    render(
      <EngineStep
        item={item({ status: 'timed_out' as EngineStatusItem['status'] })}
      />,
    );

    expect(screen.getByText('Waiting')).toBeInTheDocument();
  });
});

// ======================================================================
// Timing
// ======================================================================

describe('EngineStep timing', () => {
  it('counts a running engine up from its own start time', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    render(
      <EngineStep
        item={item({ status: 'running', duration: null })}
        startedAt="2026-01-01T00:00:00Z"
      />,
    );

    expect(screen.getByText('0s')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(65_000);
    });

    // `1m 5s`, which is a real measurement of this engine rather than the run's.
    expect(screen.getByText('1m 5s')).toBeInTheDocument();
  });

  it('prefers the live count over any duration already on the item', () => {
    // A row can carry a duration from a previous poll while an engine is still
    // running. Counting from the start time is the newer truth.
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:30Z'));

    render(
      <EngineStep
        item={item({ status: 'running', duration: '4s' })}
        startedAt="2026-01-01T00:00:00Z"
      />,
    );

    expect(screen.getByText('30s')).toBeInTheDocument();
    expect(screen.queryByText('4s')).not.toBeInTheDocument();
  });

  it('shows the recorded duration for a finished engine without counting', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    render(
      <EngineStep
        item={item({ status: 'completed', duration: '7s' })}
        startedAt="2026-01-01T00:00:00Z"
      />,
    );

    expect(screen.getByText('7s')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(300_000);
    });

    // A completed engine's duration is final. Counting it against `now` would
    // grow it for as long as the page stays open.
    expect(screen.getByText('7s')).toBeInTheDocument();
  });

  it('says Measuring when a running engine has no usable start time', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    render(
      <EngineStep item={item({ status: 'running', duration: null })} startedAt={null} />,
    );

    expect(screen.getByText('Measuring')).toBeInTheDocument();
  });

  it('reports no duration at all for an engine that has not started', () => {
    render(<EngineStep item={item({ status: 'pending', duration: null })} />);

    // "0s" would claim the engine ran and finished instantly.
    expect(screen.queryByText('0s')).not.toBeInTheDocument();
    expect(screen.queryByText('Measuring')).not.toBeInTheDocument();
  });

  it('shows nothing extra for an engine with no recorded duration', () => {
    render(<EngineStep item={item({ status: 'skipped', duration: null })} />);

    expect(screen.getByText('Skipped')).toBeInTheDocument();
  });
});

// ======================================================================
// Score and error
// ======================================================================

describe('EngineStep score and error', () => {
  it('shows the score for a completed engine', () => {
    render(<EngineStep item={item({ status: 'completed', score: 91 })} />);

    expect(screen.getByText('score 91')).toBeInTheDocument();
  });

  it('shows no score for an engine that did not produce one', () => {
    // An engine that ran but scored nothing has no score. Rendering 0 would be
    // indistinguishable from a perfect-zero measurement.
    render(<EngineStep item={item({ status: 'completed', score: null })} />);

    expect(screen.queryByText(/score/)).not.toBeInTheDocument();
  });

  it('shows no score for an engine that has not completed', () => {
    render(<EngineStep item={item({ status: 'running', score: null, duration: null })} />);

    expect(screen.queryByText(/score/)).not.toBeInTheDocument();
  });

  it('shows why an engine failed', () => {
    render(
      <EngineStep
        item={item({ status: 'failed', error: 'Semgrep exited 2: rule pack missing' })}
      />,
    );

    expect(screen.getByText('Semgrep exited 2: rule pack missing')).toBeInTheDocument();
  });

  it('shows no error line for an engine that did not fail', () => {
    render(<EngineStep item={item({ status: 'completed', error: null })} />);

    expect(screen.queryByText(/exited/)).not.toBeInTheDocument();
  });

  it('shows Failed on its own when a failure carries no message', () => {
    // Better an unexplained failure than a blank row that reads as if the engine
    // had merely not started.
    render(<EngineStep item={item({ status: 'failed', error: null })} />);

    expect(screen.getByText('Failed')).toBeInTheDocument();
  });
});

// ======================================================================
// Catalogue description
// ======================================================================

describe('EngineStep description', () => {
  it('offers the catalogue description as the name tooltip', () => {
    // The description is the service's own account of what the engine checks, so
    // it belongs on the name rather than being rewritten in the UI.
    render(<EngineStep item={item({ description: 'Checks for injection and auth flaws' })} />);

    expect(screen.getByText('Security')).toHaveAttribute(
      'title',
      'Checks for injection and auth flaws',
    );
  });

  it('falls back to the name when the catalogue has no description', () => {
    render(<EngineStep item={item({ description: '' })} />);

    expect(screen.getByText('Security')).toHaveAttribute('title', 'Security');
  });

  it('shows the name even when the catalogue knows no label', () => {
    // The builder falls back to the raw engine key before the catalogue loads.
    render(<EngineStep item={item({ name: 'error_detection', key: 'error_detection' })} />);

    expect(screen.getByText('error_detection')).toBeInTheDocument();
  });
});

// ======================================================================
// Sequence
// ======================================================================

describe('EngineStep sequence', () => {
  it('draws a connector when more steps follow', () => {
    const { container } = render(<EngineStep item={item()} isLast={false} />);

    expect(container.querySelector('li > span[aria-hidden="true"]')).toBeInTheDocument();
  });

  it('draws no connector after the last step', () => {
    // A trailing connector makes the last engine look as though something is
    // still coming after it.
    const { container } = render(<EngineStep item={item()} isLast />);

    expect(container.querySelector('li > span[aria-hidden="true"]')).not.toBeInTheDocument();
  });

  it('renders as a list item so the panel can order it', () => {
    render(<EngineStep item={item()} />);

    expect(screen.getByRole('listitem')).toBeInTheDocument();
  });
});
