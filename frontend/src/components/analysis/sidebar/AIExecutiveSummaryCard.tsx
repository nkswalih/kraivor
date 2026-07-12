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
  className,
}: {
  data: AiSummaryCard;
  isLoading?: boolean;
  className?: string;
}) {
  const summary = data.summary;
  const isAiGenerated = data.isAiGenerated;
  const busy = isLoading;

  return (
    <div className={cn('bg-card border border-border rounded-xl', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-[13px] font-semibold text-foreground flex items-center gap-1.5">
          <BotMessageSquare className="w-3.5 h-3.5 text-venom-yellow shrink-0" />
          AI Executive Summary
        </h3>
        {!isAiGenerated && (
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

      {/* Footer hint */}
      {!isAiGenerated && !busy && (
        <p className="px-4 pb-3 pt-0 text-[10px] text-text-tertiary italic border-t border-border mt-0">
          Static preview — AI summary will appear after analysis completes.
        </p>
      )}
    </div>
  );
}
