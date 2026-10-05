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

  // Three states, not two. `null` is "not measured yet", which shows a
  // placeholder; `[]` is "measured, found none", which is a real answer and
  // says so. A measured zero count still renders as 0.
  const languages = data.languages;
  const measuredLanguages = languages !== null && languages.length > 0;

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <h3 className="text-[13px] font-semibold text-foreground mb-3">
        Repository Overview
      </h3>

      {measuredLanguages && languages && (
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

      {languages === null && (
        <div className="space-y-2 mb-4" aria-hidden>
          <div className="h-1.5 rounded-full bg-krait-surface2 animate-shimmer w-full" />
          <div className="space-y-1.5">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-sm bg-krait-surface2 animate-shimmer shrink-0" />
                <div className="h-2.5 flex-1 rounded bg-krait-surface2 animate-shimmer" />
              </div>
            ))}
          </div>
        </div>
      )}

      {languages !== null && !measuredLanguages && (
        <div className="text-[11px] text-text-tertiary italic mb-4">
          No language data available yet.
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <StatTile
          icon={Files}
          iconClass="text-blue-400"
          value={data.totalFiles}
          label="Files"
        />
        <StatTile
          icon={Code2}
          iconClass="text-green-400"
          value={data.totalLines}
          label="Lines"
        />
      </div>
    </div>
  );
}

/**
 * One figure in the grid.
 *
 * Renders a shimmering block of the same height when the value is null, so the
 * layout does not jump when the number arrives, and so an unmeasured figure is
 * never confused with a measured zero.
 */
function StatTile({
  icon: Icon,
  iconClass,
  value,
  label,
}: {
  icon: typeof Files;
  iconClass: string;
  value: number | null;
  label: string;
}) {
  return (
    <div className="bg-krait-surface1 rounded-lg p-3 text-center">
      <Icon className={cn('w-4 h-4 mx-auto mb-1', iconClass)} />
      {value === null ? (
        <div
          className="h-7 my-0.5 rounded bg-krait-surface2 animate-shimmer w-2/3 mx-auto"
          aria-label={`${label} not measured yet`}
          role="status"
        />
      ) : (
        <p className="text-lg font-semibold text-foreground tabular-nums">
          {value.toLocaleString()}
        </p>
      )}
      <p className="text-[10px] text-text-tertiary uppercase tracking-wider">{label}</p>
    </div>
  );
}
