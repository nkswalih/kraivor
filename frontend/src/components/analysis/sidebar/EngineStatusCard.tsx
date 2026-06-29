'use client';

import {
  CheckCircle2,
  XCircle,
  Loader2,
  SkipForward,
  AlertTriangle,
  HelpCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { EngineStatusItem } from '@/types/domain/analysis';

interface StatusStyle {
  icon: typeof CheckCircle2;
  label: string;
  iconClass: string;
  dotClass: string;
}

const STATUS_STYLES: Record<string, StatusStyle> = {
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    iconClass: 'text-green-400',
    dotClass: 'bg-green-400',
  },
  running: {
    icon: Loader2,
    label: 'Running',
    iconClass: 'text-venom-yellow',
    dotClass: 'bg-venom-yellow',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    iconClass: 'text-red-400',
    dotClass: 'bg-red-400',
  },
  skipped: {
    icon: SkipForward,
    label: 'Skipped',
    iconClass: 'text-text-tertiary',
    dotClass: 'bg-text-tertiary',
  },
  pending: {
    icon: AlertTriangle,
    label: 'Pending',
    iconClass: 'text-text-tertiary',
    dotClass: 'bg-text-tertiary',
  },
  unavailable: {
    icon: HelpCircle,
    label: 'Unavailable',
    iconClass: 'text-text-tertiary',
    dotClass: 'bg-text-tertiary',
  },
};

function formatScore(score: number | null): string | null {
  if (score == null) return null;
  return String(score);
}

export function EngineStatusCard({
  items,
  isLoading,
  className,
}: {
  items: EngineStatusItem[];
  isLoading?: boolean;
  className?: string;
}) {
  if (isLoading) {
    return (
      <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
        <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-1/3 mb-3" />
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-4 h-4 bg-krait-surface2 rounded animate-shimmer" />
              <div className="h-3 bg-krait-surface2 rounded animate-shimmer flex-1" />
              <div className="h-3 w-8 bg-krait-surface2 rounded animate-shimmer" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <h3 className="text-[13px] font-semibold text-foreground mb-3">Engine Status</h3>
      <div className="space-y-1">
        {items.map((item) => {
          const style = STATUS_STYLES[item.status] ?? STATUS_STYLES.pending;
          const StatusIcon = style.icon;
          const scoreText = formatScore(item.score);

          return (
            <div
              key={item.key}
              className={cn(
                'flex items-center gap-2.5 px-2 py-1.5 rounded-lg transition-colors',
                item.status === 'failed' && 'bg-red-500/5',
              )}
            >
              <StatusIcon
                className={cn(
                  'w-3.5 h-3.5 shrink-0',
                  style.iconClass,
                  item.status === 'running' && 'animate-spin',
                )}
              />

              <span className="text-[12px] text-foreground flex-1 min-w-0 truncate">
                {item.name}
              </span>

              {item.status === 'failed' && item.error && (
                <span
                  className="text-[10px] text-red-400 truncate max-w-[100px]"
                  title={item.error}
                >
                  Failed
                </span>
              )}

              {item.status === 'completed' && scoreText != null && (
                <span className="text-[11px] text-text-secondary font-medium tabular-nums">
                  {scoreText}
                </span>
              )}

                      {/* Show duration for completed engines if available */}
              {item.status === 'completed' && item.duration && (
                <span className="text-[10px] text-text-tertiary tabular-nums">
                  {item.duration}
                </span>
              )}

              <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', style.dotClass)} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
