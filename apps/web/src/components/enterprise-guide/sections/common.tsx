'use client';

import { cn } from '@/lib/utils';

export function SectionCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('bg-card border border-border rounded-lg', className)}>
      {children}
    </div>
  );
}

export function SectionHeader({
  title,
  badge,
  action,
}: {
  title: string;
  badge?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-5 py-3 border-b border-border">
      <div className="flex items-center gap-2">
        <h2 className="text-[13px] font-semibold text-foreground">{title}</h2>
        {badge}
      </div>
      {action && <div className="flex items-center gap-2">{action}</div>}
    </div>
  );
}

export function SectionBody({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn('px-5 py-4', className)}>{children}</div>;
}

export function ScoreBadge({
  score,
  size = 'md',
}: {
  score: number | null | undefined;
  size?: 'sm' | 'md' | 'lg';
}) {
  if (score == null) return <span className="text-text-tertiary text-[11px]">N/A</span>;

  const color =
    score >= 90
      ? 'text-green-400'
      : score >= 75
        ? 'text-venom-yellow'
        : score >= 60
          ? 'text-venom-amber'
          : score >= 40
            ? 'text-venom-orange'
            : 'text-red-400';

  const sizeClasses = size === 'sm' ? 'text-[18px]' : size === 'lg' ? 'text-[32px]' : 'text-[24px]';

  return <span className={cn('font-bold', color, sizeClasses)}>{score}</span>;
}

export function GradeBadge({
  grade,
}: {
  grade: string | null | undefined;
}) {
  if (!grade) return null;
  const color =
    grade === 'A'
      ? 'bg-green-500/15 text-green-400 border-green-500/30'
      : grade === 'B'
        ? 'bg-venom-yellow/10 text-venom-yellow border-venom-yellow/30'
        : grade === 'C'
          ? 'bg-venom-amber/10 text-venom-amber border-venom-amber/30'
          : grade === 'D'
            ? 'bg-venom-orange/10 text-venom-orange border-venom-orange/30'
            : 'bg-red-500/15 text-red-400 border-red-500/30';
  return (
    <span
      className={cn(
        'text-[11px] font-bold px-2 py-0.5 rounded-md border',
        color,
      )}
    >
      {grade}
    </span>
  );
}

export function StatusDot({
  status,
}: {
  status: string | null | undefined;
}) {
  const color =
    status === 'excellent' || status === 'ready' || status === 'passed' || status === 'go'
      ? 'bg-green-400'
      : status === 'good' || status === 'conditional' || status === 'proceed_with_caution'
        ? 'bg-venom-yellow'
        : status === 'needs_work' || status === 'needs_attention'
          ? 'bg-venom-amber'
          : status === 'critical' || status === 'failed' || status === 'not_ready' || status === 'no_go'
            ? 'bg-red-400'
            : 'bg-text-tertiary';
  return <span className={cn('w-2 h-2 rounded-full inline-block shrink-0', color)} />;
}

export function SeverityLabel({
  severity,
}: {
  severity: string | null | undefined;
}) {
  if (!severity) return null;
  const color =
    severity === 'critical' || severity === 'P0'
      ? 'bg-red-500/15 text-red-400'
      : severity === 'high' || severity === 'P1'
        ? 'bg-venom-orange/10 text-venom-orange'
        : severity === 'medium' || severity === 'P2'
          ? 'bg-venom-amber/10 text-venom-amber'
          : 'bg-krait-surface2 text-text-tertiary';
  return (
    <span
      className={cn(
        'text-[10px] font-medium px-1.5 py-0.5 rounded uppercase tracking-wider',
        color,
      )}
    >
      {severity}
    </span>
  );
}

export function RiskBadge({ level }: { level: string | null | undefined }) {
  if (!level) return null;
  const color =
    level === 'critical'
      ? 'bg-red-500/15 text-red-400 border-red-500/30'
      : level === 'high'
        ? 'bg-venom-orange/10 text-venom-orange border-venom-orange/30'
        : level === 'medium'
          ? 'bg-venom-amber/10 text-venom-amber border-venom-amber/30'
          : 'bg-krait-surface2 text-text-tertiary border-border';
  return (
    <span
      className={cn(
        'text-[10px] font-medium px-2 py-0.5 rounded-md border uppercase tracking-wider',
        color,
      )}
    >
      {level}
    </span>
  );
}

export function HealthBar({
  score,
  className,
}: {
  score: number | null | undefined;
  className?: string;
}) {
  if (score == null) return <div className="h-1.5 rounded-full bg-krait-surface2" />;
  const color =
    score >= 90
      ? 'bg-green-400'
      : score >= 75
        ? 'bg-venom-yellow'
        : score >= 60
          ? 'bg-venom-amber'
          : score >= 40
            ? 'bg-venom-orange'
            : 'bg-red-400';
  return (
    <div className={cn('h-1.5 rounded-full bg-krait-surface2 overflow-hidden', className)}>
      <div
        className={cn('h-full rounded-full transition-all duration-500', color)}
        style={{ width: `${Math.max(2, Math.min(100, score))}%` }}
      />
    </div>
  );
}

export function DimensionRow({
  label,
  score,
  grade,
  status,
}: {
  label: string;
  score: number | null;
  grade?: string | null;
  status?: string | null;
}) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {status && <StatusDot status={status} />}
        <span className="text-[12px] text-foreground truncate">{label}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {grade && <GradeBadge grade={grade} />}
        <ScoreBadge score={score} size="sm" />
      </div>
    </div>
  );
}
