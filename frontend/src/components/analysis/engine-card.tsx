'use client';

import {
  CheckCircle2,
  XCircle,
  Loader2,
  SkipForward,
  AlertTriangle,
  HelpCircle,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProgressRing } from './progress-ring';
import type { EngineStatusItem } from '@/types/domain/analysis';

/**
 * One engine's score, as a card, for a finished run.
 *
 * Everything this card says about an engine comes from the row it is handed --
 * the same normalised `EngineStatusItem` the sidebar's engine list, the running
 * panel's steps and the failure panel's rows are built from. It used to carry
 * its own opinion instead: a five-key label table, a fifty-line function per
 * engine returning prose like "Strong security posture" from invented score
 * bands, and its own copy of the status parser.
 *
 * Three things were wrong with that, none of them cosmetic.
 *
 * The service runs nine engines. The table knew five, so `dead_code`, `errors`,
 * `simulation` and `churn` rendered as "Deadcode", "Errors", "Simulation" and
 * "Churn" -- capitalising a raw key -- and `churn`, which does real work, was
 * absent from the vocabulary entirely.
 *
 * The score bands were not the service's. Nothing in the analysis service says a
 * security score of 90 is a "strong posture"; that mapping was written in a
 * React file, so it would still be asserted about a scoring model that changed
 * underneath it. The catalogue already carries a description of what each engine
 * checks, which is a fact rather than an opinion.
 *
 * And the parser was applied to half the card: the icon and label came from
 * `parseEngineStatus`, while the description was chosen by comparing the *raw*
 * status. A row saying `"error"` drew a red X labelled "Failed" and, on the line
 * below it, "Strong security posture".
 */

interface StatusStyle {
  icon: LucideIcon;
  label: string;
  iconClass: string;
  borderClass: string;
}

const STATUS_STYLES: Record<EngineStatusItem['status'], StatusStyle> = {
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    iconClass: 'text-green-400',
    borderClass: '',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    iconClass: 'text-red-400',
    borderClass: 'border-red-500/20',
  },
  running: {
    icon: Loader2,
    label: 'Running',
    iconClass: 'text-venom-yellow',
    borderClass: 'border-venom-yellow/20',
  },
  skipped: {
    icon: SkipForward,
    label: 'Skipped',
    iconClass: 'text-text-tertiary',
    borderClass: '',
  },
  pending: {
    icon: AlertTriangle,
    label: 'Waiting',
    iconClass: 'text-text-tertiary',
    borderClass: '',
  },
  unavailable: {
    icon: HelpCircle,
    label: 'Unavailable',
    iconClass: 'text-text-tertiary',
    borderClass: '',
  },
};

export function EngineCard({
  item,
  className,
}: {
  item: EngineStatusItem;
  className?: string;
}) {
  const style = STATUS_STYLES[item.status] ?? STATUS_STYLES.pending;
  const StatusIcon = style.icon;

  // The ring is a score, so only a completed engine has one to show. Drawing it
  // for a running engine would put a number on a run that has not produced it
  // yet, and drawing the previous score after a failure would be a stale claim.
  const ringScore = item.status === 'completed' ? item.score : null;

  // A failed engine's recorded reason replaces the catalogue description in the
  // one slot the card has. "What this engine normally checks" is not the answer
  // to "why is this card red", and the old card answered it with the same
  // sentence for every engine: "Engine encountered errors during scan".
  const detail = item.status === 'failed' && item.error ? item.error : item.description;

  return (
    <div
      className={cn(
        'bg-card border rounded-xl p-4 flex flex-col items-center gap-2 transition-all duration-500 ease-out',
        'hover:border-venom-yellow/30 hover:shadow-venom',
        style.borderClass,
        item.status === 'running' && 'border-venom-yellow/40 shadow-[0_0_15px_-3px_hsl(var(--venom-yellow)/0.15)]',
        item.status === 'completed' && item.score != null && 'border-green-500/30',
        className,
      )}
    >
      <div
        className={cn(
          'transition-all duration-500 ease-out',
          item.status === 'running' && 'animate-pulse-glow',
        )}
      >
        <ProgressRing score={ringScore} size={56} strokeWidth={4} label={item.name} />
      </div>

      <div className="flex items-center gap-1.5">
        <StatusIcon
          aria-hidden="true"
          className={cn(
            'w-3.5 h-3.5 transition-colors duration-300',
            style.iconClass,
            item.status === 'running' && 'animate-spin',
          )}
        />
        <span
          className={cn(
            'text-[11px] font-medium transition-colors duration-300',
            style.iconClass,
          )}
        >
          {style.label}
        </span>
      </div>

      {detail && (
        <p
          className={cn(
            'text-[11px] text-center leading-relaxed max-w-[140px] transition-opacity duration-300',
            item.status === 'failed' ? 'text-red-400 break-words' : 'text-text-tertiary',
          )}
        >
          {detail}
        </p>
      )}
    </div>
  );
}