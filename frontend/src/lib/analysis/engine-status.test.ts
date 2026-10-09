import { describe, it, expect } from 'vitest';
import {
  countEngines,
  normalizeEngineState,
  readEngineDuration,
  readEngineError,
  readEngineStatus,
} from './engine-status';
import type { EngineStatusMap } from '@/types/domain/analysis';

/**
 * The one place in the frontend that turns an engine's recorded window into a
 * string. The progress steps and the sidebar both read its output, so a change
 * here shows up in two views that are otherwise independent -- which is why the
 * formatting is pinned rather than left to whichever copy of the arithmetic is
 * nearest.
 */

function state(overrides: Partial<{
  status: string;
  started_at: string | null;
  ended_at: string | null;
  error: string;
}> = {}): EngineStatusMap[string] {
  return {
    status: 'completed',
    started_at: '2026-01-01T00:00:00Z',
    ended_at: '2026-01-01T00:00:04Z',
    error: '',
    ...overrides,
  };
}

function map(engineId: string, value: EngineStatusMap[string]): EngineStatusMap {
  return { [engineId]: value };
}

// ======================================================================
// normalizeEngineState
// ======================================================================

describe('normalizeEngineState', () => {
  it('reads the object shape', () => {
    expect(
      normalizeEngineState({
        status: 'failed',
        started_at: '2026-01-01T00:00:00Z',
        ended_at: '2026-01-01T00:00:01Z',
        error: 'boom',
      }),
    ).toEqual({
      status: 'failed',
      startedAt: '2026-01-01T00:00:00Z',
      endedAt: '2026-01-01T00:00:01Z',
      error: 'boom',
    });
  });

  it('reads the bare-string shape left by jobs analysed before per-engine timings', () => {
    // The older shape is still in the database. Both branches have to work, or
    // the panel reads `started_at` off a string and shows nothing useful.
    expect(normalizeEngineState('running')).toEqual({
      status: 'running',
      startedAt: null,
      endedAt: null,
      error: '',
    });
  });

  it('reports an absent entry as pending, with no times and no error', () => {
    // Pending rather than failed or completed: the job has said nothing about this
    // engine, which is not the same as saying it worked.
    expect(normalizeEngineState(undefined)).toEqual({
      status: 'pending',
      startedAt: null,
      endedAt: null,
      error: '',
    });
  });
});

// ======================================================================
// readEngineStatus
// ======================================================================

describe('readEngineStatus', () => {
  it('reads a status', () => {
    expect(readEngineStatus(map('security', state({ status: 'running' })), 'security')).toBe(
      'running',
    );
  });

  it('reports pending for an engine the job says nothing about', () => {
    expect(readEngineStatus({}, 'dead_code')).toBe('pending');
  });

  it('does not throw on a null map', () => {
    expect(readEngineStatus(null, 'security')).toBe('pending');
  });
});

// ======================================================================
// readEngineError
// ======================================================================

describe('readEngineError', () => {
  it('returns the reason a failed engine failed', () => {
    expect(
      readEngineError(map('security', state({ status: 'failed', error: 'semgrep exited 2' })), 'security'),
    ).toBe('semgrep exited 2');
  });

  it('returns null for an engine that failed without giving a reason', () => {
    // Null, not an empty string -- a caller rendering `''` would print a blank
    // line where the explanation should be.
    expect(readEngineError(map('security', state({ status: 'failed' })), 'security')).toBeNull();
  });

  it.each([
    ['completed', 'It failed earlier'],
    ['running', 'It failed then restarted'],
    ['skipped', 'It failed then was skipped'],
  ])('ignores an error recorded against a %s engine', (status, error) => {
    // The status map is keyed by engine, not by attempt, so an error left on a
    // successful engine is stale bookkeeping. Reporting it would tell the user a
    // passing engine failed.
    expect(
      readEngineError(map('security', state({ status, error })), 'security'),
    ).toBeNull();
  });
});

// ======================================================================
// readEngineDuration
// ======================================================================

describe('readEngineDuration', () => {
  it('formats a window of whole seconds', () => {
    // `4s`, not `4.0s`. The trailing zero was noise on a figure that is not
    // measured to a tenth of a second -- and it disagreed with the formatter the
    // progress steps use for the same run.
    expect(readEngineDuration(map('security', state()), 'security')).toBe('4s');
  });

  it.each([
    ['2026-01-01T00:00:00Z', '2026-01-01T00:00:01Z', '1s'],
    ['2026-01-01T00:00:00Z', '2026-01-01T00:01:35Z', '1m 35s'],
    ['2026-01-01T00:00:00Z', '2026-01-01T01:05:00Z', '1h 5m'],
  ])('formats %s to %s as %s', (from, to, expected) => {
    expect(
      readEngineDuration(
        map('security', state({ started_at: from, ended_at: to })),
        'security',
      ),
    ).toBe(expected);
  });

  it('keeps milliseconds for a window under a second', () => {
    // The one case a seconds-only formatter cannot express. Flooring it to `0s`
    // would claim the engine took no time at all, which is indistinguishable from
    // a duration that was never recorded.
    expect(
      readEngineDuration(
        map('security', state({ ended_at: '2026-01-01T00:00:00.450Z' })),
        'security',
      ),
    ).toBe('450ms');
  });

  it.each([
    ['2026-01-01T00:00:00.001Z', '1ms'],
    ['2026-01-01T00:00:00.999Z', '999ms'],
  ])('keeps the millisecond a %s window actually took', (endedAt, expected) => {
    // `Date.parse` returns whole milliseconds, so the largest window still on this
    // branch is 999ms -- and it must not be rounded up into "1s", which is the
    // shared formatter's output for a full second and would be a different
    // function's answer.
    expect(
      readEngineDuration(map('security', state({ ended_at: endedAt })), 'security'),
    ).toBe(expected);
  });

  it('returns null for an engine that has not finished', () => {
    // No end time. The step counts its own time from the start instead, and a
    // `null` here is what tells it to.
    expect(
      readEngineDuration(
        map('security', state({ status: 'running', ended_at: null })),
        'security',
      ),
    ).toBeNull();
  });

  it('returns null when the job predates per-engine timings', () => {
    expect(readEngineDuration(map('security', 'completed'), 'security')).toBeNull();
  });

  it('returns null when the end precedes the start', () => {
    // Two inconsistent timestamps rather than a negative duration. Not clamped to
    // zero, which would read as an engine that finished instantly.
    expect(
      readEngineDuration(
        map('security', state({ ended_at: '2025-12-31T23:59:00Z' })),
        'security',
      ),
    ).toBeNull();
  });

  it('returns null when a timestamp cannot be parsed', () => {
    expect(
      readEngineDuration(
        map('security', state({ started_at: 'sometime' })),
        'security',
      ),
    ).toBeNull();
  });

  it('returns null for an engine the job says nothing about', () => {
    expect(readEngineDuration({}, 'simulation')).toBeNull();
  });
});

// ======================================================================
// countEngines
// ======================================================================

describe('countEngines', () => {
  it('counts only completed engines', () => {
    const statuses: EngineStatusMap = {
      security: state({ status: 'completed' }),
      churn: state({ status: 'completed' }),
      reliability: state({ status: 'running' }),
      error_detection: state({ status: 'failed' }),
      simulation: state({ status: 'skipped' }),
    };

    // Only successes. A failed engine is done, but calling it complete would
    // claim work finished when it did not.
    expect(countEngines(statuses)).toEqual({ completed: 2, total: 5 });
  });

  it('reports zeroes for an empty map rather than throwing', () => {
    expect(countEngines({})).toEqual({ completed: 0, total: 0 });
    expect(countEngines(null)).toEqual({ completed: 0, total: 0 });
  });

  it('reads the bare-string shape when counting', () => {
    expect(countEngines({ security: 'completed', churn: 'completed', dead_code: 'pending' })).toEqual({
      completed: 2,
      total: 3,
    });
  });
});
