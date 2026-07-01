'use client';

import { cn } from '@/lib/utils';

function ringColor(score: number | null | undefined): string {
  if (score == null) return 'hsl(var(--krait-border))';
  if (score >= 90) return '#22c55e';
  if (score >= 75) return '#3b82f6';
  if (score >= 60) return '#eab308';
  if (score >= 40) return '#f97316';
  return '#ef4444';
}

function ringBg(score: number | null | undefined): string {
  if (score == null) return 'hsl(var(--krait-border))';
  return 'hsl(var(--krait-border))';
}

export function ProgressRing({
  score,
  size = 48,
  strokeWidth = 4,
  label,
  className,
}: {
  score: number | null | undefined;
  size?: number;
  strokeWidth?: number;
  label?: string;
  className?: string;
}) {
  const color = ringColor(score);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = score != null ? Math.min(100, Math.max(0, score)) : 0;
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={ringBg(score)}
            strokeWidth={strokeWidth}
          />
          {score != null && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          {score != null ? (
            <span className="text-[11px] font-semibold tabular-nums" style={{ color }}>
              {score}
            </span>
          ) : (
            <span className="text-[9px] text-text-tertiary">N/A</span>
          )}
        </div>
      </div>
      {label && (
        <span className="text-[10px] text-text-tertiary uppercase tracking-wider text-center leading-tight">
          {label}
        </span>
      )}
    </div>
  );
}
