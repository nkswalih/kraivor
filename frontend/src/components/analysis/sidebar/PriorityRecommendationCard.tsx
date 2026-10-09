'use client';

import { ArrowRight, CheckCircle2, Container, FileCode2, Shield, Wrench, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SeverityBadge } from '@/components/analysis/severity-badge';
import type { PriorityRecommendation } from '@/types/domain/analysis';

const categoryIcons: Record<string, typeof Shield> = {
  performance: Zap,
  security: Shield,
  maintainability: FileCode2,
  quality: Wrench,
  devops: Container,
};

const impactColors: Record<string, string> = {
  high: 'text-red-400 bg-red-500/10',
  medium: 'text-yellow-400 bg-yellow-500/10',
  low: 'text-blue-400 bg-blue-500/10',
};

const difficultyColors: Record<string, string> = {
  high: 'text-red-400 bg-red-500/10',
  medium: 'text-yellow-400 bg-yellow-500/10',
  low: 'text-green-400 bg-green-500/10',
};

export function PriorityRecommendationCard({
  data,
  isLoading,
  isRunning,
  isError,
  className,
  onViewFinding,
}: {
  data: PriorityRecommendation | null;
  isLoading?: boolean;
  /**
   * The run still has stages ahead of it. The builder returns null on an
   * in-flight job because no conclusion exists yet, and that null has nothing
   * to show -- unlike a finished run's null, which *is* its conclusion.
   */
  isRunning?: boolean;
  /**
   * The findings fetch did not come back. Unknown is not empty: the card
   * would be claiming a clean run on evidence it never received.
   */
  isError?: boolean;
  className?: string;
  onViewFinding?: () => void;
}) {
  if (isLoading) {
    return (
      <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
        <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-1/2 mb-3" />
        <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-full mb-2" />
        <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-4/5 mb-4" />
        <div className="flex gap-3 mb-4">
          <div className="h-6 bg-krait-surface2 rounded animate-shimmer w-16" />
          <div className="h-6 bg-krait-surface2 rounded animate-shimmer w-16" />
          <div className="h-6 bg-krait-surface2 rounded animate-shimmer w-16" />
        </div>
        <div className="h-8 bg-krait-surface2 rounded animate-shimmer w-full" />
      </div>
    );
  }

  if (!data) {
    // Four ways to arrive at a null, and only the last one has anything to
    // say. Still loading was handled above. A run with stages ahead of it has
    // no conclusion to quote, so the card stays out of the way -- exactly what
    // the analysing view has always shown. A failed fetch proves nothing about
    // the run. The fourth is a finished run whose findings really are empty:
    // that is an answer, and the card gives it instead of reaching for advice
    // nobody measured.
    if (isRunning || isError) return null;

    return (
      <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
        <h3 className="text-[13px] font-semibold text-foreground mb-3">
          Highest Priority Recommendation
        </h3>
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-green-500/10 shrink-0">
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          </div>
          <div>
            <p className="text-[13px] font-medium text-foreground">
              No findings recorded for this run
            </p>
            <p className="text-[11px] text-text-secondary mt-1 leading-relaxed">
              Nothing to prioritise — the run completed without filing an
              active finding.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const Icon = categoryIcons[data.category] ?? Shield;

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <h3 className="text-[13px] font-semibold text-foreground">
          Highest Priority Recommendation
        </h3>
        {data.severity && (
          <SeverityBadge severity={data.severity} className="shrink-0" />
        )}
      </div>

      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 rounded-lg bg-venom-yellow/10 shrink-0">
          <Icon className="w-4 h-4 text-venom-yellow" />
        </div>
        <div className="min-w-0">
          <p className="text-[13px] font-medium text-foreground">{data.title}</p>
          <p className="text-[11px] text-text-secondary mt-1 leading-relaxed line-clamp-4">
            {data.description}
          </p>
          {data.filePath && (
            <p className="flex items-center gap-1 mt-1.5 text-[10px] font-mono text-text-secondary">
              <FileCode2 className="w-3 h-3 shrink-0" />
              <span className="truncate">
                {`${data.filePath}${data.lineStart != null ? `:${data.lineStart}` : ''}`}
              </span>
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full', impactColors[data.impact])}>
          {data.impact.charAt(0).toUpperCase() + data.impact.slice(1)} Impact
        </span>
        <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full', difficultyColors[data.difficulty])}>
          {data.difficulty.charAt(0).toUpperCase() + data.difficulty.slice(1)} Difficulty
        </span>
        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-krait-surface2 text-text-secondary">
          {data.estimatedTime}
        </span>
      </div>

      {data.findingId && (
        <button
          onClick={onViewFinding}
          className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg border border-border bg-krait-surface1 hover:bg-white/5 transition-colors text-[11px] font-medium text-foreground group"
        >
          View Finding
          <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
        </button>
      )}
    </div>
  );
}
