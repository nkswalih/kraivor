'use client';

import { Tiers } from '@/types/domain/analysis';

function scoreColor(score: number): string {
  if (score >= 90) return '#22c55e';
  if (score >= 75) return '#3b82f6';
  if (score >= 60) return '#eab308';
  if (score >= 40) return '#f97316';
  return '#ef4444';
}

function scoreTier(score: number): Tiers {
  if (score >= 90) return Tiers.PRODUCTION_READY;
  if (score >= 75) return Tiers.MINOR_ISSUES;
  if (score >= 60) return Tiers.NEEDS_WORK;
  if (score >= 40) return Tiers.SIGNIFICANT_RISK;
  return Tiers.CRITICAL_STATE;
}

const TIER_LABELS: Record<Tiers, string> = {
  [Tiers.PRODUCTION_READY]: 'Production Ready',
  [Tiers.MINOR_ISSUES]: 'Minor Issues',
  [Tiers.NEEDS_WORK]: 'Needs Work',
  [Tiers.SIGNIFICANT_RISK]: 'Significant Risk',
  [Tiers.CRITICAL_STATE]: 'Critical State',
};

export function ScoreGauge({
  score,
  size = 120,
  strokeWidth = 8,
  label,
}: {
  score: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = scoreColor(score);
  const tier = scoreTier(score);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--krait-border))"
          strokeWidth={strokeWidth}
        />
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
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-2xl font-semibold text-text-primary" style={{ color }}>
          {score}
        </span>
      </div>
      {label && <span className="text-[11px] text-text-tertiary uppercase tracking-wider">{label}</span>}
      {!label && score > 0 && (
        <span className="text-[11px] text-text-tertiary font-medium" style={{ color }}>
          {TIER_LABELS[tier]}
        </span>
      )}
    </div>
  );
}
