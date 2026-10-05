'use client';

import { XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProgressBar } from '@/components/analysis/progress-bar';
import {
  elapsedBetween,
  formatDuration,
  usableTimestamp,
} from '@/lib/format/duration';
import { EngineStep } from './EngineStep';
import type { AnalysisJob, EngineStatusItem } from '@/types/domain/analysis';

/**
 * What a run that stopped, and why.
 *
 * The failed block this replaces was three sentences and a grid of engine cards,
 * and it could answer none of the questions someone actually opens a failed job
 * to ask: what broke, what still worked, and where it got to. The reason was
 * either the raw traceback or the literal words "Unknown error" -- the first
 * because nothing reduced it, the second because a missing message was rendered
 * as a message.
 *
 * The engine rows come from the same builder output the running panel and the
 * sidebar read, and they render through the same `EngineStep`, so an engine looks
 * the same here as it did three minutes before it failed. That is the point: the
 * failure is not a different view of the run, it is the same view after the end
 * of it.
 *
 * Nothing here ticks. No start times are passed to the steps, so no step counts,
 * because there is no clock running. A row the service still has as `running` on
 * a failed job would render as "Measuring" -- visibly wrong, but inert, and a
 * fabrication to "fix" it by relabelling the state would be worse.
 */

export interface JobFailurePanelProps {
  job: AnalysisJob;
  /** Per-engine rows, already normalised by the insights builder. */
  items: EngineStatusItem[];
  className?: string;
}

export function JobFailurePanel({ job, items, className }: JobFailurePanelProps) {
  const total = items.length;
  const completed = items.filter((i) => i.status === 'completed').length;
  const failed = items.filter((i) => i.status === 'failed').length;
  const skipped = items.filter((i) => i.status === 'skipped').length;
  const waiting = items.filter((i) => i.status === 'pending').length;
  const unreported = items.filter((i) => i.status === 'unavailable').length;

  // Anything that is no longer in a waiting state has stopped, whatever it
  // stopped as. A failed engine is finished work, so it counts here -- leaving it
  // out would understate how much of the run actually happened.
  const settled = completed + failed + skipped;

  // Measured between the two instants the run recorded. Not against `now`: a
  // failed run is over, so a figure measured to the current time would keep
  // growing for as long as the page stayed open.
  const elapsed = formatDuration(
    elapsedBetween(usableTimestamp(job.started_at), job.completed_at),
  );

  return (
    <div className={cn('space-y-6', className)}>
      <div className="flex items-start gap-3">
        <XCircle
          aria-hidden="true"
          className="w-[18px] h-[18px] shrink-0 text-red-400 mt-px"
        />
        <div className="min-w-0">
          <p className="text-[13px] font-medium text-red-400">Analysis failed</p>
          {job.error_message ? (
            <p className="text-[12px] text-text-secondary mt-1 break-words">
              {job.error_message}
            </p>
          ) : (
            // The service records no reason for some failures -- a job cancelled
            // out from under the pipeline, or a row written by an older version
            // before the message existed. "Unknown error" claimed an error was
            // there and could not be read. This says what is true: there is no
            // reason, and that is a gap in the record rather than a mystery.
            <p className="text-[12px] text-text-tertiary mt-1">
              No failure reason was recorded for this run.
            </p>
          )}
        </div>
      </div>

      {/* Where it stopped. The bar holds the percentage the run actually reached
          -- it is not rewound on failure, so it is the honest amount of work done
          and not a fresh start. */}
      <ProgressBar pct={job.progress_pct} message={job.progress_message} />

      {total > 0 && (
        <p className="text-[12px] text-text-tertiary">
          {describeWhatFinished(settled, total, failed, waiting, unreported)}
          {elapsed ? ` · ran for ${elapsed}` : ''}
        </p>
      )}

      {items.length === 0 ? (
        <p className="text-[12px] text-text-tertiary">
          No engines reported for this run.
        </p>
      ) : (
        <ol className="space-y-0">
          {items.map((item, index) => (
            <EngineStep key={item.key} item={item} isLast={index === items.length - 1} />
          ))}
        </ol>
      )}
    </div>
  );
}

/**
 * How much of the run happened, in the parts a reader can act on.
 *
 * Only the non-zero parts are named. "0 engines failed" is noise on a run where
 * nothing failed, and "5 never started" is the fact that tells you the failure
 * cut the run short rather than merely spoiling one engine.
 */
function describeWhatFinished(
  settled: number,
  total: number,
  failed: number,
  waiting: number,
  unreported: number,
): string {
  const parts = [`${settled} of ${total} engines finished`];
  if (failed > 0) parts.push(`${failed} failed`);
  if (waiting > 0) parts.push(`${waiting} never started`);
  // "Unavailable" means the service could not say. Naming it separately keeps
  // "never started" meaning exactly what it says.
  if (unreported > 0) parts.push(`${unreported} not reported`);
  return parts.join(' · ');
}