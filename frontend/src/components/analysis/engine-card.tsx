'use client';

import {
  CheckCircle2,
  XCircle,
  Loader2,
  SkipForward,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProgressRing } from './progress-ring';

const ENGINE_LABELS: Record<string, string> = {
  security: 'Security',
  reliability: 'Reliability',
  maintainability: 'Maintainability',
  devops: 'DevOps',
  performance: 'Performance',
};

const ENGINE_DESCRIPTIONS: Record<string, (score: number | null | undefined, status: string | undefined) => string> = {
  security: (s, st) => {
    if (st === 'failed') return 'Engine encountered errors during scan';
    if (st === 'running') return 'Scanning for vulnerabilities...';
    if (st === 'skipped' || st === 'pending') return 'Awaiting execution';
    if (s == null) return 'No security issues found';
    if (s >= 90) return 'Strong security posture';
    if (s >= 75) return 'Minor security concerns';
    if (s >= 60) return 'Moderate security risks';
    return 'Critical vulnerabilities detected';
  },
  reliability: (s, st) => {
    if (st === 'failed') return 'Engine encountered errors during scan';
    if (st === 'running') return 'Analyzing reliability patterns...';
    if (st === 'skipped' || st === 'pending') return 'Awaiting execution';
    if (s == null) return 'No reliability issues found';
    if (s >= 90) return 'Highly reliable codebase';
    if (s >= 75) return 'Minor reliability gaps';
    if (s >= 60) return 'Reliability needs improvement';
    return 'Significant reliability risks';
  },
  maintainability: (s, st) => {
    if (st === 'failed') return 'Engine encountered errors during scan';
    if (st === 'running') return 'Evaluating code structure...';
    if (st === 'skipped' || st === 'pending') return 'Awaiting execution';
    if (s == null) return 'No maintainability issues found';
    if (s >= 90) return 'Well-structured, easy to maintain';
    if (s >= 75) return 'Generally maintainable code';
    if (s >= 60) return 'Code complexity needs attention';
    return 'Poor maintainability, refactor needed';
  },
  devops: (s, st) => {
    if (st === 'failed') return 'Engine encountered errors during scan';
    if (st === 'running') return 'Checking DevOps practices...';
    if (st === 'skipped' || st === 'pending') return 'Awaiting execution';
    if (s == null) return 'No DevOps issues found';
    if (s >= 90) return 'Excellent DevOps practices';
    if (s >= 75) return 'Good DevOps with minor gaps';
    if (s >= 60) return 'DevOps needs improvement';
    return 'Critical DevOps gaps detected';
  },
  performance: (s, st) => {
    if (st === 'failed') return 'Engine encountered errors during scan';
    if (st === 'running') return 'Analyzing performance metrics...';
    if (st === 'skipped' || st === 'pending') return 'Awaiting execution';
    if (s == null) return 'No performance issues found';
    if (s >= 90) return 'High-performance codebase';
    if (s >= 75) return 'Good performance overall';
    if (s >= 60) return 'Performance bottlenecks present';
    return 'Significant performance concerns';
  },
};

function defaultDescription(engine: string, score: number | null | undefined, status: string | undefined): string {
  const desc = ENGINE_DESCRIPTIONS[engine];
  if (desc) return desc(score, status);
  if (status === 'failed') return 'Engine encountered errors';
  if (status === 'running') return 'Currently running...';
  if (status === 'skipped' || status === 'pending') return 'Awaiting execution';
  if (score == null) return 'Analysis complete';
  if (score >= 75) return 'Good results';
  return 'Needs attention';
}

type EngineStatus = 'completed' | 'failed' | 'running' | 'skipped' | 'pending';

const STATUS_CONFIG: Record<EngineStatus, { icon: typeof CheckCircle2; label: string; ringClass: string; borderClass: string }> = {
  completed: { icon: CheckCircle2, label: 'Completed', ringClass: 'text-green-400', borderClass: '' },
  failed: { icon: XCircle, label: 'Failed', ringClass: 'text-red-400', borderClass: 'border-red-500/20' },
  running: { icon: Loader2, label: 'Running', ringClass: 'text-venom-yellow', borderClass: 'border-venom-yellow/20' },
  skipped: { icon: SkipForward, label: 'Skipped', ringClass: 'text-text-tertiary', borderClass: '' },
  pending: { icon: AlertTriangle, label: 'Pending', ringClass: 'text-text-tertiary', borderClass: '' },
};

function parseEngineStatus(raw: string | undefined): EngineStatus {
  if (!raw) return 'pending';
  const lower = raw.toLowerCase();
  if (lower === 'completed' || lower === 'success') return 'completed';
  if (lower === 'failed' || lower === 'error') return 'failed';
  if (lower === 'running' || lower === 'in_progress') return 'running';
  if (lower === 'skipped') return 'skipped';
  return 'pending';
}

export function EngineCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-xl p-4 flex flex-col items-center gap-3 animate-fade-up">
      <div className="w-14 h-14 rounded-full bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
      <div className="h-4 w-20 rounded bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
      <div className="h-3 w-16 rounded bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
      <div className="h-3 w-28 rounded bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
    </div>
  );
}

export function EngineCard({
  engine,
  status,
  score,
}: {
  engine: string;
  status: string | undefined;
  score: number | null | undefined;
}) {
  const parsed = parseEngineStatus(status);
  const StatusIcon = STATUS_CONFIG[parsed].icon;
  const label = ENGINE_LABELS[engine] ?? engine.charAt(0).toUpperCase() + engine.slice(1);
  const description = defaultDescription(engine, score, status);

  const ringScore = parsed === 'completed' ? score : undefined;

  return (
    <div
      className={cn(
        'bg-card border rounded-xl p-4 flex flex-col items-center gap-2 transition-all duration-500 ease-out',
        'hover:border-venom-yellow/30 hover:shadow-venom',
        STATUS_CONFIG[parsed].borderClass,
        parsed === 'running' && 'border-venom-yellow/40 shadow-[0_0_15px_-3px_hsl(var(--venom-yellow)/0.15)]',
        parsed === 'completed' && ringScore != null && 'border-green-500/30',
      )}
    >
      <div className={cn(
        'transition-all duration-500 ease-out',
        parsed === 'running' && 'animate-pulse-glow',
      )}>
        <ProgressRing score={ringScore} size={56} strokeWidth={4} label={label} />
      </div>

      <div className="flex items-center gap-1.5">
        <StatusIcon
          className={cn(
            'w-3.5 h-3.5 transition-colors duration-300',
            STATUS_CONFIG[parsed].ringClass,
            parsed === 'running' && 'animate-spin',
          )}
        />
        <span className={cn('text-[11px] font-medium transition-colors duration-300', STATUS_CONFIG[parsed].ringClass)}>
          {STATUS_CONFIG[parsed].label}
        </span>
      </div>

      <p className="text-[11px] text-text-tertiary text-center leading-relaxed max-w-[140px] transition-opacity duration-300">
        {description}
      </p>
    </div>
  );
}
