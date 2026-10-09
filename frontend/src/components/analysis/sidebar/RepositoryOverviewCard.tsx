'use client';

import {
  Files,
  Code2,
  Braces,
  FunctionSquare,
  Route,
  Package,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RepositoryOverview } from '@/types/domain/analysis';

/**
 * One language's share, as a reader should see it.
 *
 * The backend now reports two decimals so a real 0.011% survives the round
 * trip, and rendering it raw would put "0.011%" in a column whose other
 * entries are "53.5%". Three cases, because three different things are true:
 *
 * - exactly `0` is a measured zero -- the file set contained that language and
 *   none of its lines counted, so print `0%` and mean it;
 * - non-zero below `0.1` is a real share too small to spell out; `0%` would be
 *   a lie and `0.04%` would be noise, so `<0.1%`;
 * - everything else is one decimal, which is what the column always showed.
 *
 * Exported because the `aria-label` on the bar uses it: a screen reader
 * announcing "0%" for a language that is present is the same defect in
 * another medium.
 */
export function formatShare(percentage: number): string {
  if (percentage === 0) return '0%';
  if (percentage < 0.1) return '<0.1%';
  return `${percentage.toFixed(1)}%`;
}

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
        <div className="grid grid-cols-2 gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-[74px] bg-krait-surface2 rounded-lg animate-shimmer"
            />
          ))}
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
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-foreground">
          Repository Overview
        </h3>
        {measuredLanguages && languages && (
          <span className="text-[10px] text-text-tertiary tabular-nums">
            {languages.length} {languages.length === 1 ? 'language' : 'languages'}
          </span>
        )}
      </div>

      {measuredLanguages && languages && (
        <div className="space-y-2 mb-4">
          <div
            className="flex h-2 gap-px rounded-full overflow-hidden bg-krait-surface2 ring-1 ring-inset ring-border"
            role="img"
            aria-label={`Language composition: ${languages
              .map((l) => `${l.name} ${formatShare(l.percentage)}`)
              .join(', ')}`}
          >
            {languages.map((lang) => (
              <div
                key={lang.name}
                className="h-full transition-all duration-500 motion-reduce:transition-none"
                style={{
                  // The raw value: this is a CSS length, not a label.
                  width: `${lang.percentage}%`,
                  backgroundColor: lang.color,
                }}
                title={`${lang.name} — ${formatShare(lang.percentage)}`}
              />
            ))}
          </div>
          <ul className="space-y-1.5">
            {languages.map((lang) => (
              <li key={lang.name} className="flex items-center gap-2 text-[11px]">
                {/* The ring keeps GitHub's darker entries (JSON, Dockerfile, C)
                    legible against a dark card, where a bare dot of #292929
                    disappears entirely. */}
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0 ring-1 ring-black/40"
                  style={{ backgroundColor: lang.color }}
                  aria-hidden
                />
                <span className="text-text-secondary flex-1 truncate">{lang.name}</span>
                <span className="text-foreground font-medium tabular-nums">
                  {formatShare(lang.percentage)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {languages === null && (
        <div className="space-y-2 mb-4" aria-hidden>
          <div className="h-2 rounded-full bg-krait-surface2 animate-shimmer w-full" />
          <div className="space-y-1.5">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-krait-surface2 animate-shimmer shrink-0" />
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

      <p className="text-[10px] text-text-tertiary font-medium uppercase tracking-wider mb-2">
        Measured
      </p>
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
        <StatTile
          icon={Braces}
          iconClass="text-purple-400"
          value={data.classes}
          label="Classes"
        />
        <StatTile
          icon={FunctionSquare}
          iconClass="text-cyan-400"
          value={data.functions}
          label="Functions"
        />
        <StatTile
          icon={Route}
          iconClass="text-amber-400"
          value={data.endpoints}
          label="Endpoints"
        />
        <StatTile
          icon={Package}
          iconClass="text-pink-400"
          value={data.frameworks}
          label="Frameworks"
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
    <div className="bg-krait-surface1 border border-border/60 rounded-lg p-3 text-center">
      <Icon className={cn('w-4 h-4 mx-auto mb-1', iconClass)} aria-hidden />
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
