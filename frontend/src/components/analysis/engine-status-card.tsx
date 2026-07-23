'use client';

import {
  CheckCircle2,
  XCircle,
  Loader2,
  SkipForward,
  AlertTriangle,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProgressRing } from './progress-ring';

const ENGINE_LABELS: Record<string, string> = {
  security: 'Security',
  reliability: 'Reliability',
  maintainability: 'Maintainability',
  devops: 'DevOps',
  performance: 'Performance',
  dead_code: 'Dead Code',
  errors: 'Error Patterns',
  simulation: 'Simulation',
};

type EngineStatus = 'completed' | 'failed' | 'running' | 'skipped' | 'pending';

const STATUS_CONFIG: Record<
  EngineStatus,
  { icon: LucideIcon; label: string; ringClass: string; dotClass: string }
> = {
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    ringClass: 'text-green-400',
    dotClass: 'bg-green-400',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    ringClass: 'text-red-400',
    dotClass: 'bg-red-400',
  },
  running: {
    icon: Loader2,
    label: 'Running',
    ringClass: 'text-venom-yellow',
    dotClass: 'bg-venom-yellow',
  },
  skipped: {
    icon: SkipForward,
    label: 'Skipped',
    ringClass: 'text-text-tertiary',
    dotClass: 'bg-text-tertiary',
  },
  pending: {
    icon: AlertTriangle,
    label: 'Pending',
    ringClass: 'text-text-tertiary',
    dotClass: 'bg-text-tertiary',
  },
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

export function EngineStatusCard({
  engine,
  status,
  score,
  className,
}: {
  engine: string;
  status: string | undefined;
  score: number | null | undefined;
  className?: string;
}) {
  const parsed = parseEngineStatus(status);
  const StatusIcon = STATUS_CONFIG[parsed].icon;
  const label = ENGINE_LABELS[engine] ?? engine.charAt(0).toUpperCase() + engine.slice(1);

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border border-border bg-card p-3 transition-all hover:border-venom-yellow/20',
        parsed === 'failed' && 'border-red-500/20 hover:border-red-500/30',
        parsed === 'running' && 'border-venom-yellow/20',
        className,
      )}
    >
      <ProgressRing score={parsed === 'completed' ? score : undefined} size={42} strokeWidth={3} />

      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-foreground truncate">{label}</p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <StatusIcon
            className={cn(
              'w-3 h-3',
              STATUS_CONFIG[parsed].ringClass,
              parsed === 'running' && 'animate-spin',
            )}
          />
          <span className={cn('text-[11px]', STATUS_CONFIG[parsed].ringClass)}>
            {STATUS_CONFIG[parsed].label}
            {parsed === 'completed' && status !== 'completed' && status ? ` (${status})` : ''}
          </span>
        </div>
      </div>

      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', STATUS_CONFIG[parsed].dotClass)} />
    </div>
  );
}
