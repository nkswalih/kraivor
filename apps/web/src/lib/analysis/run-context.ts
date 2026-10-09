/**
 * Which stage of a run has produced something yet.
 *
 * The sidebar shows a repository's own facts while the analysis is still
 * working out what those facts are. Each fact becomes available at a known
 * point in the pipeline, and the difference between "not yet" and "measured,
 * and there is none" is the difference between a placeholder and a result.
 *
 * The thresholds come from `pipeline.py`'s stage progress weights. They are
 * named after the stage that produces the fact rather than written as bare
 * percentages, so that if a stage's weight changes there is one place to change
 * it and everything downstream follows.
 */

/** Clone writes the file count, line count and language mix at this point. */
export const CLONE_COMPLETE_PCT = 15;

/** Parse writes a first batch of entity counts at this point. */
export const PARSE_PROGRESSING_PCT = 25;

/** Parse is finished, so its counts will not move again. */
export const PARSE_COMPLETE_PCT = 60;

export type RunFact<T> =
  /** Nothing has measured this yet. Carries where the progress has got to. */
  | { state: 'pending'; progressPct: number; availableFromPct: number }
  /** Measured. `settled` is false while the stage producing it is still going. */
  | { state: 'ready'; value: T; settled: boolean };

/**
 * Wrap a value in the question the panel actually needs answered.
 *
 * A null or undefined value is `pending`, not zero and not an empty list: the
 * stage that produces it has not run. When it has run, the value is `ready`, and
 * `settled` says whether the stage that produces it has finished -- so a panel
 * can mark a figure as still moving instead of implying it is final.
 *
 * `settlesAtPct` is the progress at which the producing stage completes. For a
 * clone-stage fact that is `CLONE_COMPLETE_PCT` itself, which means anything
 * ready is already settled.
 */
export function measure<T>(
  value: T | null | undefined,
  progressPct: number,
  availableFromPct: number,
  settlesAtPct: number = availableFromPct,
): RunFact<NonNullable<T>> {
  if (value == null) {
    return { state: 'pending', progressPct, availableFromPct };
  }
  return { state: 'ready', value, settled: progressPct >= settlesAtPct };
}
