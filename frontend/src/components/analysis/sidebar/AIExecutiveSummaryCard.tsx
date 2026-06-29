'use client';

import { cn } from '@/lib/utils';
import type { AiSummaryCard } from '@/types/domain/analysis';

export function AIExecutiveSummaryCard({
  data,
  isLoading,
  className,
}: {
  data: AiSummaryCard;
  isLoading?: boolean;
  className?: string;
}) {
  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-foreground flex items-center gap-1.5">
          <span className="text-[15px]">✨</span>
          AI Executive Summary
        </h3>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-venom-yellow/10 text-venom-yellow font-medium uppercase tracking-wider">
          Coming Soon
        </span>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer" />
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-11/12" />
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-4/5" />
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-3/4" />
        </div>
      ) : (
        <p className="text-[12px] text-text-secondary leading-relaxed">
          {data.summary}
        </p>
      )}

      <p className="mt-3 text-[10px] text-text-tertiary italic border-t border-border pt-3">
        Static Preview — This summary will automatically be generated after AI analysis becomes available.
      </p>

      {/* TODO: Replace fallback summary with AI Service endpoint */}
      {/* Kafka AnalysisCompleted event will populate aiSummary */}
    </div>
  );
}
