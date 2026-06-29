'use client';

import { ArrowRight, Shield, Zap, FileCode2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PriorityRecommendation } from '@/types/domain/analysis';

const categoryIcons: Record<string, typeof Shield> = {
  performance: Zap,
  security: Shield,
  maintainability: FileCode2,
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
  className,
  onViewFinding,
}: {
  data: PriorityRecommendation;
  isLoading?: boolean;
  className?: string;
  onViewFinding?: () => void;
}) {
  const Icon = categoryIcons[data.category] ?? Shield;

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

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <h3 className="text-[13px] font-semibold text-foreground mb-3">
        Highest Priority Recommendation
      </h3>

      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 rounded-lg bg-venom-yellow/10 shrink-0">
          <Icon className="w-4 h-4 text-venom-yellow" />
        </div>
        <div>
          <p className="text-[13px] font-medium text-foreground">{data.title}</p>
          <p className="text-[11px] text-text-secondary mt-1 leading-relaxed">
            {data.description}
          </p>
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

      {/* TODO: Replace with AI-powered recommendation */}
    </div>
  );
}
