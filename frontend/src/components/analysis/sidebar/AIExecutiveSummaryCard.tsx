'use client';

import { cn } from '@/lib/utils';
import type { AiSummaryCard } from '@/types/domain/analysis';
import { BotMessageSquare } from 'lucide-react';
import { MarkdownRenderer } from '@/components/ui/markdown/markdown-renderer';
import { AiSummaryErrorPanel } from '@/components/analysis/ai-summary/AiSummaryErrorPanel';

function SummarySkeleton() {
  return (
    <div className="space-y-2.5 p-1">
      {[100, 88, 75, 92, 66].map((w, i) => (
        <div
          key={i}
          className="h-2.5 rounded bg-krait-surface2 animate-shimmer"
          style={{ width: `${w}%` }}
        />
      ))}
    </div>
  );
}

export function AIExecutiveSummaryCard({
  data,
  isLoading,
  isRunning,
  guidePending = false,
  guideError = null,
  onRefetchGuide,
  onRetry,
  isRetrying = false,
  className,
}: {
  data: AiSummaryCard;
  isLoading?: boolean;
  /**
   * Whether the analysis is still going.
   *
   * Distinct from `isLoading`, which means the job itself has not loaded yet.
   * The two look identical in this card -- both render the skeleton -- but they
   * differ in what may be claimed around it: a run in progress has no summary
   * yet and one coming, whereas a finished run without one has a real gap.
   */
  isRunning?: boolean;
  /**
   * Whether the guide request is still in flight.
   *
   * The third distinct cause of an absent summary, and the reason the other two
   * props are not enough. A finished run with no summary may have none at all,
   * or may simply not have been read yet -- and only the caller can tell those
   * apart, because it owns the request. Without it, a completed page flashes an
   * empty card labelled "Preview" promising a summary that was already on its
   * way.
   */
  guidePending?: boolean;
  /**
   * The guide request itself failed.
   *
   * A fourth cause of an absent summary, and the one that had no handling at
   * all: `useEnterpriseGuide` sets `retry: false`, so a single failed request left
   * this card claiming a summary was on its way for the rest of the page's life.
   *
   * Deliberately not the same as `data.error`. That one is the service reporting
   * that generation failed, which is a fact about the run. This one is us failing
   * to find out, which is a fact about the connection -- and it must never be
   * rendered as though something is known about the summary.
   */
  guideError?: Error | null;
  /** Re-run the guide request. Only offered where retrying could work. */
  onRefetchGuide?: () => void;
  /**
   * Ask the service to generate the summary again.
   *
   * Optional, and passed straight through to the error panel, which is what
   * decides whether to offer it at all. A card with no `onRetry` still shows the
   * reason -- the reason is worth showing to someone who cannot act on it -- it
   * just shows no button.
   */
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}) {
  const summary = data.summary;
  const isAiGenerated = data.isAiGenerated;
  // A summary is expected but not here yet in all three cases, and all three
  // render the same placeholder.
  const busy = isLoading || isRunning || guidePending === true;

  // Checked before everything else. With no answer there is nothing to say about
  // the summary -- not that it failed, not that it is coming -- so this takes
  // precedence over both `data.error` and the footer's promise. `guidePending`
  // is in `busy`, so a failed request is only reached once loading has settled.
  const unreadable = Boolean(guideError) && !busy;

  // A recorded failure. Distinct from every other absent summary, and the reason
  // the card has three separate props at all: a run that finished and produced no
  // summary because one was never attempted is a different thing from one that
  // tried and was refused, and this is the state that can say which.
  //
  // Only meaningful when the summary is genuinely absent. `insights-builder` drops
  // the error when a summary exists, so this cannot be a summary plus an error
  // here; the guard is because `data` is a plain object and nothing stops a
  // caller handing one over.
  const error = !isAiGenerated && !busy && !unreadable ? (data.error ?? null) : null;

  // While the run is going there is no summary and none is expected, so the
  // "Preview" badge would be labelling a card with nothing in it, and the
  // footer said the summary "will appear after analysis completes" on a job
  // where nothing is complete. Both claims are false until the run ends -- and
  // false for an unreadable guide as well, which is a third thing entirely.
  const showPreviewBadge = !isAiGenerated && !busy && !error && !unreadable;
  // Suppressed whenever a summary is still expected, suppressed for a recorded
  // failure, and suppressed when we could not read the guide at all --
  // "will appear after analysis completes" on a run that has completed and
  // failed to produce one, or on a request that failed, is the exact sentence
  // this component exists to stop saying.
  const showFooter = !isAiGenerated && !busy && !error && !unreadable;

  return (
    <div className={cn('bg-card border border-border rounded-xl', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-[13px] font-semibold text-foreground flex items-center gap-1.5">
          <BotMessageSquare className="w-3.5 h-3.5 text-venom-yellow shrink-0" />
          AI Executive Summary
        </h3>
        {showPreviewBadge && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-venom-yellow/10 text-venom-yellow font-medium uppercase tracking-wider shrink-0">
            Preview
          </span>
        )}
      </div>

      {/* Body with independent scroll */}
      <div className="max-h-[360px] overflow-y-auto px-4 py-3 scrollbar-thin">
        {busy ? (
          <SummarySkeleton />
        ) : unreadable ? (
          /* Not `AiSummaryErrorPanel`. Nothing is known about the summary, so
             there is no envelope to render and no `code` to map -- and passing a
             synthesised one would claim the service had classified a failure it
             never saw. */
          <div role="status" className="text-[11px] text-text-secondary">
            <p className="text-[12px] font-medium text-foreground">
              Couldn&apos;t load the summary
            </p>
            <p className="text-text-tertiary mt-1">
              The request for this run&apos;s report did not come back. Nothing is
              known about the summary itself.
            </p>
            {onRefetchGuide && (
              <button
                onClick={onRefetchGuide}
                className="mt-2 px-2 py-1 rounded-md border border-border bg-card text-[11px] text-text-secondary hover:text-foreground hover:border-venom-yellow/30 transition-colors"
              >
                Try again
              </button>
            )}
          </div>
        ) : error ? (
          <AiSummaryErrorPanel error={error} onRetry={onRetry} isRetrying={isRetrying} />
        ) : (
          <MarkdownRenderer content={summary} compact />
        )}
      </div>

      {showFooter && (
        <p className="px-4 pb-3 pt-0 text-[10px] text-text-tertiary italic border-t border-border mt-0">
          Static preview — AI summary will appear after analysis completes.
        </p>
      )}
    </div>
  );
}
