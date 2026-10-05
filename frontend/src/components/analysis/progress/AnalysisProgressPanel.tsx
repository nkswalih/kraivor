'use client';

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProgressBar } from '@/components/analysis/progress-bar';
import { elapsedBetween, formatDuration, useElapsedSeconds, usableTimestamp } from '@/lib/format/duration';
import { EngineStep } from './EngineStep';
import { normalizeEngineState } from '@/lib/analysis/engine-status';
import { JobStatus } from '@/types/domain/analysis';
import type { AnalysisJob, EngineStatusMap, EngineStatusItem } from '@/types/domain/analysis';

/**
 * What a run is doing right now.
 *
 * Three things, in the order a person watching a run actually wants them: how far
 * along it is, what is happening this second, and where every engine stands. The
 * per-engine rows come from the same normalised shape the sidebar's engine card
 * uses, so the two cannot disagree about an engine's state.
 *
 * The run timer ticks only while the run is in flight. A job that has ended is
 * described by `started_at` and `completed_at` and its duration is final -- the
 * panel is only mounted for running jobs, but the prop is honoured rather than
 * assumed, because a component that renders correctly only for its one caller is
 * a component that breaks when it gets a second.
 */

/**
 * Whether this run can still make progress.
 *
 * Deliberately not the builder's `isJobInFlight`, which asks a different
 * question: that one asks "does this job still have a report to describe?", so it
 * treats a failed run as in flight -- a failed run does have partial results
 * worth showing in the sidebar. This one asks "is the clock still running?", so a
 * failed run is settled and its duration must stop. Reaching for the shared helper
 * here would leave a failed job counting up forever.
 */
function isStillProgressing(status: JobStatus): boolean {
  return status !== JobStatus.COMPLETED && status !== JobStatus.FAILED;
}

export interface AnalysisProgressPanelProps {
  job: AnalysisJob;
  /** Per-engine state, keyed by engine id. */
  engineStatuses: EngineStatusMap;
  /** Per-engine rows, already normalised by the insights builder. */
  items: EngineStatusItem[];
  className?: string;
}

export function AnalysisProgressPanel({
  job,
  engineStatuses,
  items,
  className,
}: AnalysisProgressPanelProps) {
  const startedAt = usableTimestamp(job.started_at);
  const stillGoing = isStillProgressing(job.status);
  const live = useElapsedSeconds(startedAt, stillGoing);

  const total = items.length;
  const settled = items.filter(
    (i) => i.status === 'completed' || i.status === 'failed' || i.status === 'skipped',
  ).length;
  const failed = items.filter((i) => i.status === 'failed').length;

  const elapsed = stillGoing
    ? formatDuration(live)
    : // A settled run is described by the two instants it recorded, not by how
      // long ago it started. Measuring to `now` would report a run that finished
      // ten minutes ago as still taking ten minutes, and would keep growing.
      formatDuration(elapsedBetween(startedAt, job.completed_at));

  return (
    <div className={cn('space-y-6', className)}>
      <ProgressBar pct={job.progress_pct} message={job.progress_message} />

      {/* What is happening this second, and how long it has been happening. */}
      <div className="flex items-center justify-between gap-3 text-[12px] text-text-tertiary">
        <span className="flex items-center gap-1.5 min-w-0">
          <Loader2
            aria-hidden="true"
            className="w-3.5 h-3.5 text-venom-yellow animate-spin shrink-0"
          />
          <span className="truncate" aria-live="polite">
            {job.progress_message || 'Analysis in progress'}
          </span>
        </span>

        <span className="shrink-0 tabular-nums">
          {elapsed
            ? `${settled} of ${total} engines · ${elapsed}`
            : `${settled} of ${total} engines`}
        </span>
      </div>

      {/* A failure partway through changes what the run is doing, and the bar
          alone would keep advancing as though nothing had gone wrong. */}
      {failed > 0 && (
        <p className="text-[12px] text-red-400">
          {failed === 1 ? '1 engine failed' : `${failed} engines failed`} — the
          run continues without {failed === 1 ? 'it' : 'them'}.
        </p>
      )}

      {items.length === 0 ? (
        <p className="text-[12px] text-text-tertiary">
          No engines reported for this run.
        </p>
      ) : (
        <ol className="space-y-0">
          {items.map((item, index) => (
            <EngineStep
              key={item.key}
              item={item}
              // Only the running engine needs a start time, and only it will
              // count with it -- so the lookup is not paid for nine times.
              startedAt={
                item.status === 'running'
                  ? normalizeEngineState(engineStatuses?.[item.key]).startedAt
                  : null
              }
              isLast={index === items.length - 1}
            />
          ))}
        </ol>
      )}
    </div>
  );
}
