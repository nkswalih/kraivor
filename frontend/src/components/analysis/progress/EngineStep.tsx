'use client';

import {
  CheckCircle2,
  XCircle,
  Loader2,
  SkipForward,
  Circle,
  HelpCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDuration, useElapsedSeconds } from '@/lib/format/duration';
import type { EngineStatusItem } from '@/types/domain/analysis';

/**
 * One engine in a run, as a step: where it is, and how long it has taken.
 *
 * This is a different question from the sidebar's engine card, which asks "what
 * state is each engine in" for a finished run. A step asks "what is happening
 * now, what is next, and how long has the current one been going" -- so it carries
 * a live timer for the engine that is running, and says so plainly for the ones
 * that have not started.
 *
 * Every state the service can report gets its own rendering. The old engine card
 * mapped five of them onto descriptions written per engine, which meant a sixth
 * engine rendered as "Awaiting execution" forever and a failed one could not say
 * why.
 */

interface StateStyle {
  icon: typeof CheckCircle2;
  label: string;
  iconClass: string;
  /** The connector drawn above the icon, so a step reads as part of a sequence. */
  connectorClass: string;
  spin: boolean;
}

const STATE_STYLES: Record<EngineStatusItem['status'], StateStyle> = {
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    iconClass: 'text-green-400',
    connectorClass: 'bg-green-500/40',
    spin: false,
  },
  running: {
    icon: Loader2,
    label: 'Running',
    iconClass: 'text-venom-yellow',
    connectorClass: 'bg-venom-yellow/50',
    spin: true,
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    iconClass: 'text-red-400',
    connectorClass: 'bg-red-500/40',
    spin: false,
  },
  skipped: {
    icon: SkipForward,
    label: 'Skipped',
    iconClass: 'text-text-tertiary',
    connectorClass: 'bg-krait-border',
    spin: false,
  },
  pending: {
    icon: Circle,
    label: 'Waiting',
    iconClass: 'text-text-tertiary',
    connectorClass: 'bg-krait-border',
    spin: false,
  },
  unavailable: {
    icon: HelpCircle,
    label: 'Unavailable',
    iconClass: 'text-text-tertiary',
    connectorClass: 'bg-krait-border',
    spin: false,
  },
};

export interface EngineStepProps {
  item: EngineStatusItem;
  /** The engine's own start time, for the live timer. */
  startedAt?: string | null;
  /** Last step in the list: no connector below it. */
  isLast?: boolean;
  className?: string;
}

export function EngineStep({
  item,
  startedAt = null,
  isLast = false,
  className,
}: EngineStepProps) {
  const style = STATE_STYLES[item.status] ?? STATE_STYLES.pending;
  const StateIcon = style.icon;

  // Only the engine actually running gets a clock. A finished engine's duration
  // is already recorded, and a queued one has nothing to count from.
  const live = useElapsedSeconds(startedAt, item.status === 'running');

  const duration =
    item.status === 'running'
      ? (formatDuration(live) ?? 'Measuring')
      : item.duration;

  return (
    <li
      className={cn('relative flex gap-3 pb-3 last:pb-0', className)}
      aria-current={item.status === 'running' ? 'step' : undefined}
    >
      {/* The connector. Sits above the icon so the list reads top to bottom as
          the order the pipeline runs, and stops on the last row. */}
      {!isLast && (
        <span
          aria-hidden="true"
          className={cn(
            'absolute left-[9px] top-5 bottom-0 w-px',
            style.connectorClass,
          )}
        />
      )}

      <StateIcon
        aria-hidden="true"
        className={cn(
          'relative z-10 w-[18px] h-[18px] shrink-0 bg-card rounded-full mt-px',
          style.iconClass,
          // `motion-reduce:animate-none` rather than a `useReducedMotion()` hook,
          // unlike the marketing components. This is a static class on a
          // condition, so the media query answers it in CSS: no hook, no state,
          // no re-render, and correct on the server-rendered markup too. A
          // client-side hook would arrive one frame late and flicker the
          // animation first. The plan called for the hook; this is better for
          // this case and the reason is recorded here rather than left to be
          // "corrected" back.
          style.spin && 'animate-spin motion-reduce:animate-none',
        )}
      />

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2 min-w-0">
          <span
            className="text-[12px] text-foreground font-medium truncate"
            // The description comes from the service's engine catalogue, so it is
            // the pipeline's own account of what this engine checks rather than a
            // label written in the UI.
            title={item.description || item.name}
          >
            {item.name}
          </span>
          <span className={cn('text-[10px] shrink-0', style.iconClass)}>
            {style.label}
          </span>
        </div>

        {/* Duration for every state that has one, and a live count for the one
            still going. Pending steps say nothing rather than "0s", which would
            read as an engine that ran instantly. */}
        {duration && (
          <span className="text-[10px] text-text-tertiary tabular-nums">
            {duration}
          </span>
        )}

        {item.status === 'completed' && item.score != null && (
          <span className="text-[10px] text-text-secondary tabular-nums ml-2">
            score {item.score}
          </span>
        )}

        {item.status === 'failed' && item.error && (
          <p className="text-[11px] text-red-400 mt-0.5 break-words">
            {item.error}
          </p>
        )}
      </div>
    </li>
  );
}
