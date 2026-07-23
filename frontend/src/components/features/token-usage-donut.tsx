'use client';

import type { DailyUsage } from '@/types/domain/ai';

function usageColor(pct: number): string {
  if (pct >= 85) return '#ef4444';
  if (pct >= 60) return '#f97316';
  if (pct >= 35) return '#eab308';
  return '#22c55e';
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(n);
}

export function TokenUsageDonut({
  usage,
  size = 16,
  className,
}: {
  usage: DailyUsage | undefined;
  size?: number;
  className?: string;
}) {
  if (!usage || usage.limit <= 0) return null;

  const pct = Math.min(100, (usage.used / usage.limit) * 100);
  const strokeW = 2.5;
  const radius = (size - strokeW) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const color = usageColor(pct);

  return (
    <div
      className={`relative group flex items-center ${className ?? ''}`}
    >
      <svg width={size} height={size} className="-rotate-90 shrink-0">
        {/* Gray background ring — always visible */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#52525b"
          strokeWidth={strokeW}
        />
        {/* Colored progress ring */}
        {pct > 0 && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeW}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
        )}
      </svg>

      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 rounded-lg bg-krait-surface3 border border-krait-border text-[11px] text-text-primary whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150 z-50 shadow-lg">
        <div className="font-medium mb-0.5">{usage.used.toLocaleString()} / {usage.limit.toLocaleString()}</div>
        <div className="text-text-tertiary">{formatTokens(usage.remaining)} remaining today</div>
      </div>
    </div>
  );
}
