'use client';

import { cn } from '@/lib/utils';
import { Shield, Zap, FileCode2, ArrowRight, TriangleAlert, Clock, Gauge } from 'lucide-react';

const categoryConfig: Record<string, { icon: typeof Shield; label: string }> = {
  performance: { icon: Zap, label: 'Performance' },
  security: { icon: Shield, label: 'Security' },
  maintainability: { icon: FileCode2, label: 'Maintainability' },
  quality: { icon: TriangleAlert, label: 'Quality' },
  devops: { icon: Gauge, label: 'DevOps' },
};

const impactColors: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/10 border-red-500/20',
  high: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  low: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
};

export function PriorityRecommendationSection({
  issue,
  isLoading,
}: {
  issue: Record<string, string> | null | undefined;
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-lg p-5">
        <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-44 mb-4" />
        <div className="flex items-start gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-krait-surface2 animate-shimmer shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-3/4" />
            <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-full" />
            <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-5/6" />
          </div>
        </div>
        <div className="flex gap-2">
          <div className="h-5 bg-krait-surface2 rounded animate-shimmer w-20" />
          <div className="h-5 bg-krait-surface2 rounded animate-shimmer w-24" />
          <div className="h-5 bg-krait-surface2 rounded animate-shimmer w-16" />
        </div>
      </div>
    );
  }

  if (!issue || !issue.title) {
    return null;
  }

  const category = (issue.category || '').toLowerCase();
  const config = categoryConfig[category] ?? { icon: TriangleAlert, label: category || 'Issue' };
  const Icon = config.icon;
  const severity = (issue.severity || 'high').toLowerCase();
  const severityColor = impactColors[severity] ?? impactColors.high;

  return (
    <div className="bg-card border border-border rounded-lg">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border">
        <h2 className="text-[13px] font-semibold text-foreground flex items-center gap-2">
          <TriangleAlert className="w-4 h-4 text-venom-yellow" />
          Top Priority Recommendation
        </h2>
      </div>
      <div className="p-5">
        <div className="flex items-start gap-3 mb-4">
          <div className={cn('p-2 rounded-lg border shrink-0', severityColor)}>
            <Icon className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-medium text-foreground">{issue.title}</p>
            {issue.file_path && (
              <p className="text-[11px] font-mono text-text-secondary mt-1 truncate">{issue.file_path}</p>
            )}
            {issue.description && (
              <p className="text-[12px] text-text-secondary mt-2 leading-relaxed">{issue.description}</p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full border', severityColor)}>
            {severity.charAt(0).toUpperCase() + severity.slice(1)} Severity
          </span>
          {issue.estimated_effort && (
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-krait-surface3 text-text-secondary border border-border flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {issue.estimated_effort}m
            </span>
          )}
        </div>

        {issue.recommendation && (
          <div className="bg-krait-surface3 border border-border rounded-lg p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">Recommendation</p>
            <p className="text-[12px] text-foreground leading-relaxed">{issue.recommendation}</p>
          </div>
        )}
      </div>
    </div>
  );
}
