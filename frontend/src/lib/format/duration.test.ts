import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  elapsedBetween,
  elapsedSince,
  formatDuration,
  useElapsedSeconds,
  usableTimestamp,
} from './duration';

/**
 * Three consumers now share this: the sidebar's elapsed row, the progress panel's
 * run timer, and each engine step's own timer. The rules that matter are that an
 * unusable input yields absence rather than a number, and that a run which has
 * ended stops being measured against `now`.
 */

afterEach(() => {
  vi.useRealTimers();
});

// ======================================================================
// usableTimestamp
// ======================================================================

describe('usableTimestamp', () => {
  it('passes a real ISO timestamp through', () => {
    expect(usableTimestamp('2026-01-01T00:00:00Z')).toBe('2026-01-01T00:00:00Z');
  });

  it.each([
    ['null', null],
    ['undefined', undefined],
    ['an empty string', ''],
  ])('rejects %s', (_label, value) => {
    expect(usableTimestamp(value)).toBeNull();
  });

  it('rejects a string that is not a date', () => {
    // Not merely unusual. `formatRelativeTime` falls through to
    // `Intl.DateTimeFormat.format` when the date will not parse, and that throws
    // `RangeError` on an invalid `Date` -- so an unguarded timestamp takes the
    // whole panel down instead of costing one row.
    expect(usableTimestamp('not-a-date')).toBeNull();
  });

  it('rejects a date the platform cannot represent', () => {
    // A syntactically valid ISO string can still be out of range, and `Date.parse`
    // answers NaN rather than throwing, so this is a real rejection and not a
    // caught exception.
    expect(usableTimestamp('2026-13-45T99:99:99Z')).toBeNull();
  });
});

// ======================================================================
// elapsedSince
// ======================================================================

describe('elapsedSince', () => {
  it('counts from the start time to now', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    expect(elapsedSince('2025-12-31T23:59:00Z')).toBe(60);
  });

  it('floors partial seconds rather than showing them', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:12.900Z'));

    // 12.9s would flicker between two values on a counter that updates once a
    // second, and each looks like a typo.
    expect(elapsedSince('2026-01-01T00:00:00Z')).toBe(12);
  });

  it.each([
    ['no start time', null],
    ['an unparseable start time', 'never'],
  ])('returns null for %s', (_label, startedAt) => {
    expect(elapsedSince(startedAt)).toBeNull();
  });

  it('returns null when the clock is behind the recorded start', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    // Clock skew, not a run that started in the future. A negative elapsed time
    // would read as a bug rather than as two machines disagreeing.
    expect(elapsedSince('2026-01-01T01:00:00Z')).toBeNull();
  });
});

// ======================================================================
// elapsedBetween
// ======================================================================

describe('elapsedBetween', () => {
  it('measures the gap between two recorded instants', () => {
    expect(
      elapsedBetween('2026-01-01T00:00:00Z', '2026-01-01T00:02:00Z'),
    ).toBe(120);
  });

  it('returns zero for two identical instants', () => {
    expect(elapsedBetween('2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')).toBe(0);
  });

  it('goes negative when the end precedes the start', () => {
    // Not clamped here. The caller decides: a duration shown as 0s would claim a
    // run took no time, which is a different claim from "these two timestamps are
    // inconsistent".
    expect(elapsedBetween('2026-01-01T00:02:00Z', '2026-01-01T00:00:00Z')).toBe(-120);
  });

  it.each([
    ['a missing start', null, '2026-01-01T00:00:00Z'],
    ['a missing end', '2026-01-01T00:00:00Z', null],
    ['an unparseable start', 'never', '2026-01-01T00:00:00Z'],
    ['an unparseable end', '2026-01-01T00:00:00Z', 'never'],
    ['both missing', null, null],
  ])('returns null for %s', (_label, from, to) => {
    expect(elapsedBetween(from, to)).toBeNull();
  });
});

// ======================================================================
// formatDuration
// ======================================================================

describe('formatDuration', () => {
  it.each([
    [0, '0s'],
    [9, '9s'],
    [59, '59s'],
    [60, '1m 0s'],
    [95, '1m 35s'],
    [3599, '59m 59s'],
    [3600, '1h 0m'],
    [3900, '1h 5m'],
    [7325, '2h 2m'],
  ])('formats %i seconds as %s', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected);
  });

  it('drops the seconds past an hour', () => {
    // A run past an hour has usually finished, and a second count on it is noise
    // rather than information.
    expect(formatDuration(3661)).toBe('1h 1m');
  });

  it.each([
    ['null', null],
    ['undefined', undefined],
    ['a negative value', -5],
    ['NaN', Number.NaN],
    ['Infinity', Number.POSITIVE_INFINITY],
  ])('returns null for %s rather than a nonsensical string', (_label, value) => {
    // Every one of these would otherwise render as a literal, since the comparisons
    // inside are all false for NaN.
    expect(formatDuration(value)).toBeNull();
  });

  it('truncates rather than rounding', () => {
    // 119.7s is one minute and fifty-nine point seven seconds, not two minutes.
    expect(formatDuration(119.7)).toBe('1m 59s');
  });
});

// ======================================================================
// useElapsedSeconds
// ======================================================================

describe('useElapsedSeconds', () => {
  it('counts up once a second while ticking', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    const { result } = renderHook(() =>
      useElapsedSeconds('2026-01-01T00:00:00Z', true),
    );

    expect(result.current).toBe(0);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current).toBe(5);
  });

  it('stops counting when told not to tick', () => {
    // The finished-run case. Measured against `now` it would report a duration
    // that keeps growing for as long as the page is open, and on a failed run it
    // would never stop at all.
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    const { result } = renderHook(() =>
      useElapsedSeconds('2026-01-01T00:00:00Z', false),
    );

    expect(result.current).toBe(0);

    act(() => {
      vi.advanceTimersByTime(600_000);
    });

    expect(result.current).toBe(0);
  });

  it('starts no interval when there is no start time', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    const { result } = renderHook(() => useElapsedSeconds(null, true));

    expect(result.current).toBeNull();

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    // Still null, and no timer was ever set -- a queued job would otherwise run a
    // once-a-second interval for as long as it sat in the queue.
    expect(result.current).toBeNull();
  });

  it('recomputes when the start time changes', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:01:00Z'));

    const { result, rerender } = renderHook(
      ({ startedAt }: { startedAt: string }) => useElapsedSeconds(startedAt, true),
      { initialProps: { startedAt: '2026-01-01T00:00:00Z' } },
    );

    expect(result.current).toBe(60);

    // A job that only just got a start time moves from "not started" to counting
    // from that moment.
    rerender({ startedAt: '2026-01-01T00:00:30Z' });

    expect(result.current).toBe(30);
  });

  it('reports a clock behind the start as null rather than negative', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));

    const { result } = renderHook(() =>
      useElapsedSeconds('2026-01-01T02:00:00Z', true),
    );

    expect(result.current).toBeNull();
  });
});
