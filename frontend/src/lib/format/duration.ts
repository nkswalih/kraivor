'use client';

import { useEffect, useState } from 'react';

/**
 * Elapsed-time arithmetic and formatting, shared by the places that show how
 * long something took.
 *
 * Two rules run through all of it, and both exist because the alternative reads
 * as a bug on screen:
 *
 *   - An unusable timestamp is absence, never a number. `null` covers "no
 *     value", "empty string" and "not a date", and callers render a placeholder
 *     rather than `NaN` or `0`.
 *   - A duration is measured between two recorded instants, or from a start to
 *     *now* while something is still going. Measuring a finished run to `now`
 *     reports it as still taking time, and grows for as long as the page is
 *     open.
 */

/**
 * A timestamp this code can use, or null.
 *
 * `formatDate` and `Intl.DateTimeFormat` both end in a call that throws
 * `RangeError` on an invalid `Date`, so an unparseable value has to be caught
 * before it reaches them -- one bad timestamp should cost one row, not the
 * panel it is in.
 */
export function usableTimestamp(value: string | null | undefined): string | null {
  if (!value) return null;
  return Number.isNaN(Date.parse(value)) ? null : value;
}

/** Seconds since `startedAt`, or null when the clock cannot be trusted. */
export function elapsedSince(startedAt: string | null): number | null {
  if (!startedAt) return null;
  const start = Date.parse(startedAt);
  if (Number.isNaN(start)) return null;
  const seconds = Math.floor((Date.now() - start) / 1000);
  // Negative means this machine's clock is behind the one that wrote the
  // timestamp. Guessing there would put an absurd elapsed time on screen.
  return seconds < 0 ? null : seconds;
}

/** Seconds from one recorded timestamp to another, or null if either is unusable. */
export function elapsedBetween(
  from: string | null | undefined,
  to: string | null | undefined,
): number | null {
  const a = usableTimestamp(from ?? null);
  const b = usableTimestamp(to ?? null);
  if (a === null || b === null) return null;
  return Math.floor((Date.parse(b) - Date.parse(a)) / 1000);
}

/**
 * `42s`, `2m 14s`, `1h 5m`.
 *
 * Two units below an hour and one above it, because a run long enough to need
 * seconds has usually finished, and a run past an hour no longer has a
 * meaningful second count.
 */
export function formatDuration(seconds: number | null | undefined): string | null {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return null;
  const whole = Math.floor(seconds);
  if (whole < 60) return `${whole}s`;
  if (whole < 3600) return `${Math.floor(whole / 60)}m ${whole % 60}s`;
  return `${Math.floor(whole / 3600)}h ${Math.floor((whole % 3600) / 60)}m`;
}

/**
 * Seconds elapsed since `startedAt`, counting up once a second while `tick` is
 * true and frozen the rest of the time.
 *
 * `tick` is the caller's judgement, not a guess: a run in flight counts, and a
 * run that has ended is described by its two timestamps instead. An interval
 * that keeps firing for a finished job is a number that keeps moving for no
 * reason, and on a failed run it would never stop.
 *
 * Returns null when there is no usable start time, which is distinct from zero:
 * zero would claim a run took no time at all.
 */
export function useElapsedSeconds(
  startedAt: string | null,
  tick: boolean,
): number | null {
  const [elapsed, setElapsed] = useState<number | null>(() => elapsedSince(startedAt));

  useEffect(() => {
    setElapsed(elapsedSince(startedAt));
    if (!tick || !startedAt) return;

    const timer = setInterval(() => setElapsed(elapsedSince(startedAt)), 1000);
    return () => clearInterval(timer);
  }, [startedAt, tick]);

  return elapsed;
}
