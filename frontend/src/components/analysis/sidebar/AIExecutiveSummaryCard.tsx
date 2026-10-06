'use client';

import { cn } from '@/lib/utils';
import type { AiSummaryCard } from '@/types/domain/analysis';
import { BotMessageSquare, Sparkles } from 'lucide-react';
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
   * Optional, and offered in the two places where it could work: a recorded
   * failure, via the error panel, and an absent summary, via this card's own
   * empty state. The error panel still decides for itself whether a retry is
   * worth offering -- an `auth_failed` is not.
   *
   * A card with no `onRetry` still shows the reason -- the reason is worth
   * showing to someone who cannot act on it -- it just shows no button.
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

  // The run is finished, the guide has been read, and there is neither a
  // summary nor a reason for its absence -- the stage simply never produced
  // one. `insights-builder` hands over `summary: ''` for that, which used to
  // fall through to `MarkdownRenderer` and render an empty body under a
  // "Preview" badge and a footer promising the summary "will appear after
  // analysis completes" -- on a job that had already completed. Nothing to
  // read, with nothing offered to fix it, which is the worst possible shape
  // for a card a reader opens expecting a summary.
  //
  // It is also the one absence here where something can actually be done:
  // `onRetry` re-runs enrichment, which is the request that would produce one.
  const missing = !isAiGenerated && !busy && !error && !unreadable;

  return (
    <div className={cn('bg-card border border-border rounded-xl', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-[13px] font-semibold text-foreground flex items-center gap-1.5">
          <BotMessageSquare className="w-3.5 h-3.5 text-venom-yellow shrink-0" />
          AI Executive Summary
        </h3>
        {/* No badge. "Preview" only ever rendered alongside the empty body
            below, where it labelled a card with nothing in it -- a header
            promising a preview of an absent summary is the first thing that
            read as broken. */}
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
        ) : missing ? (
          /* No summary and no recorded reason: the stage never produced one.
             Said rather than rendered as an empty box, and offered the one
             action that could change it -- the guide page's section has had
             this state from the start, and this card was the surface that
             lacked it. */
          <div role="status" className="text-[11px] text-text-secondary">
            <p className="text-[12px] font-medium text-foreground">
              No AI summary for this run
            </p>
            <p className="text-text-tertiary mt-1">
              This run finished without producing one. Everything else in this
              report is unaffected.
            </p>
            {onRetry && (
              <button
                onClick={onRetry}
                disabled={isRetrying}
                className="mt-2 flex items-center gap-1.5 px-2 py-1 rounded-md border border-border bg-card text-[11px] text-text-secondary hover:text-foreground hover:border-venom-yellow/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Sparkles
                  aria-hidden="true"
                  className={cn('w-3 h-3', isRetrying && 'animate-spin motion-reduce:animate-none')}
                />
                {isRetrying ? 'Generating...' : 'Generate AI summary'}
              </button>
            )}
          </div>
        ) : (
          <MarkdownRenderer content={summary} compact />
        )}
      </div>
    </div>
  );
}
