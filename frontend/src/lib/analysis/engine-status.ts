import type { EngineState, EngineStatusMap } from '@/types/domain/analysis';

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
 */
export function readEngineDuration(
  statuses: EngineStatusMap | null | undefined,
  engineId: string,
): string | null {
  const { startedAt, endedAt } = normalizeEngineState(statuses?.[engineId]);
  if (!startedAt || !endedAt) return null;
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime();
  if (!Number.isFinite(ms) || ms < 0) return null;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60_000);
  return `${minutes}m ${Math.round((ms % 60_000) / 1000)}s`;
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