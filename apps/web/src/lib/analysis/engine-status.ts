import type { EngineState, EngineStatusMap } from '@/types/domain/analysis';
import { formatDuration } from '@/lib/format/duration';

/**
 * An `engine_statuses` entry reduced to one shape the UI can rely on.
 *
 * The map is keyed by engine id and each value is either the current
 * `EngineState` object or, for jobs analysed before per-engine timings existed,
 * a bare status string. Read it through here rather than indexing the map
 * directly, so every consumer handles both.
 */
export interface NormalizedEngineState {
  status: string;
  startedAt: string | null;
  endedAt: string | null;
  error: string;
}

const EMPTY: NormalizedEngineState = {
  status: 'pending',
  startedAt: null,
  endedAt: null,
  error: '',
};

/** Reduce one map entry, whatever shape it arrived in. */
export function normalizeEngineState(
  entry: EngineState | string | null | undefined,
): NormalizedEngineState {
  if (entry == null) return EMPTY;
  if (typeof entry === 'string') {
    return { ...EMPTY, status: entry };
  }
  return {
    status: entry.status ?? EMPTY.status,
    startedAt: entry.started_at ?? null,
    endedAt: entry.ended_at ?? null,
    error: entry.error ?? '',
  };
}

/** Status for one engine id, or `pending` when the job has nothing for it. */
export function readEngineStatus(
  statuses: EngineStatusMap | null | undefined,
  engineId: string,
): string {
  return normalizeEngineState(statuses?.[engineId]).status;
}

/** Why an engine failed, or null when it did not fail or gave no reason. */
export function readEngineError(
  statuses: EngineStatusMap | null | undefined,
  engineId: string,
): string | null {
  const { status, error } = normalizeEngineState(statuses?.[engineId]);
  return status === 'failed' && error ? error : null;
}

/**
 * How long an engine took, from its own recorded window.
 *
 * Returns null while an engine is still running or when the job predates
 * per-engine timings, so callers render a placeholder rather than "0s".
 *
 * A second and above, this defers to the shared formatter. It used to carry its
 * own copy of the same three branches, and the progress steps use the shared one
 * -- so the sidebar and the running panel would have rendered the same recorded
 * window two different ways. Only the sub-second case stays here, because a
 * seconds-only format cannot express it without lying.
 */
export function readEngineDuration(
  statuses: EngineStatusMap | null | undefined,
  engineId: string,
): string | null {
  const { startedAt, endedAt } = normalizeEngineState(statuses?.[engineId]);
  if (!startedAt || !endedAt) return null;
  const ms = Date.parse(endedAt) - Date.parse(startedAt);
  if (!Number.isFinite(ms) || ms < 0) return null;
  // An engine that finished inside a second would floor to "0s", claiming it took
  // no time at all -- which is what a genuinely unrecorded duration looks like.
  // `Date.parse` yields whole milliseconds, so this is never a fraction.
  if (ms < 1000) return `${ms}ms`;
  return formatDuration(ms / 1000);
}

/** Completed and total engine counts for a progress summary. */
export function countEngines(statuses: EngineStatusMap | null | undefined): {
  completed: number;
  total: number;
} {
  const entries = Object.values(statuses ?? {});
  return {
    completed: entries.filter((e) => normalizeEngineState(e).status === 'completed').length,
    total: entries.length,
  };
}