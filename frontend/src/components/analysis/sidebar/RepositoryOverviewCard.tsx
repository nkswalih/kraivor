'use client';

import { Files, Code2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RepositoryOverview } from '@/types/domain/analysis';

export function RepositoryOverviewCard({
  data,
  isLoading,
  className,
}: {
  data: RepositoryOverview;
  isLoading?: boolean;
  className?: string;
}) {
  if (isLoading) {
    return (
      <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
        <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-1/3 mb-4" />
        <div className="space-y-2 mb-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="h-3 w-12 bg-krait-surface2 rounded animate-shimmer" />
              <div className="flex-1 h-2 bg-krait-surface2 rounded-full animate-shimmer" />
              <div className="h-3 w-8 bg-krait-surface2 rounded animate-shimmer" />
            </div>
          ))}
        </div>
        <div className="flex gap-4">
          <div className="h-10 bg-krait-surface2 rounded animate-shimmer w-1/2" />
          <div className="h-10 bg-krait-surface2 rounded animate-shimmer w-1/2" />
        </div>
      </div>
    );
  }

  const languages = data.languages;
  const hasLanguages = languages.length > 0;

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <h3 className="text-[13px] font-semibold text-foreground mb-3">
        Repository Overview
      </h3>

      {hasLanguages && (
        <div className="space-y-2 mb-4">
          <div className="flex h-1.5 rounded-full overflow-hidden bg-krait-surface2">
            {languages.map((lang) => (
              <div
                key={lang.name}
                className="h-full transition-all duration-500"
                style={{
                  width: `${lang.percentage}%`,
                  backgroundColor: lang.color,
                }}
              />
            ))}
          </div>
          <div className="space-y-1.5">
            {languages.map((lang) => (
              <div key={lang.name} className="flex items-center gap-2 text-[11px]">
                <span
                  className="w-2 h-2 rounded-sm shrink-0"
                  style={{ backgroundColor: lang.color }}
                />
                <span className="text-text-secondary flex-1">{lang.name}</span>
                <span className="text-foreground font-medium tabular-nums">
                  {lang.percentage}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasLanguages && (
        <div className="text-[11px] text-text-tertiary italic mb-4">
          No language data available yet.
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div className="bg-krait-surface1 rounded-lg p-3 text-center">
          <Files className="w-4 h-4 text-blue-400 mx-auto mb-1" />
          <p className="text-lg font-semibold text-foreground tabular-nums">
            {data.totalFiles.toLocaleString()}
          </p>
          <p className="text-[10px] text-text-tertiary uppercase tracking-wider">Files</p>
        </div>
        <div className="bg-krait-surface1 rounded-lg p-3 text-center">
          <Code2 className="w-4 h-4 text-green-400 mx-auto mb-1" />
          <p className="text-lg font-semibold text-foreground tabular-nums">
            {data.totalLines.toLocaleString()}
          </p>
          <p className="text-[10px] text-text-tertiary uppercase tracking-wider">Lines</p>
        </div>
      </div>
    </div>
  );
}
