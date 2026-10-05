'use client';

import { cn } from '@/lib/utils';
import type { AiSummaryCard } from '@/types/domain/analysis';
import { BotMessageSquare } from 'lucide-react';
import { MarkdownRenderer } from '@/components/ui/markdown/markdown-renderer';

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
  className?: string;
}) {
  const summary = data.summary;
  const isAiGenerated = data.isAiGenerated;
  const busy = isLoading || isRunning;

  // While the run is going there is no summary and none is expected, so the
  // "Preview" badge would be labelling a card with nothing in it, and the
  // footer said the summary "will appear after analysis completes" on a job
  // where nothing is complete. Both claims are false until the run ends.
  const showPreviewBadge = !isAiGenerated && !isRunning;
  // Suppressed in all three states where no summary exists yet: the job has not
  // loaded, the run has not finished, or the summary was not generated.
  const showFooter = !isAiGenerated && !isLoading && !isRunning;

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
        ) : (
          <MarkdownRenderer content={summary} compact />
        )}
      </div>

      {/* Footer hint. Wording is deliberately not changed for a finished run
          whose summary never arrived: that is a real gap rather than a pending
          one, and giving it an honest message of its own belongs with the error
          handling that will say which failure it was. */}
      {showFooter && (
        <p className="px-4 pb-3 pt-0 text-[10px] text-text-tertiary italic border-t border-border mt-0">
          Static preview — AI summary will appear after analysis completes.
        </p>
      )}
    </div>
  );
}
