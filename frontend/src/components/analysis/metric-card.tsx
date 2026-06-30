'use client';

import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

export function MetricCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-xl p-4 flex items-center gap-4 animate-fade-up h-[88px]">
      <div className="w-10 h-10 rounded-lg bg-surface2 animate-shimmer shrink-0" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
      <div className="flex-1 space-y-2">
        <div className="h-6 w-16 rounded bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
        <div className="h-3 w-20 rounded bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
      </div>
    </div>
  );
}

export function MetricCard({
  icon: Icon,
  value,
  label,
  className,
  onClick,
}: {
  icon: LucideIcon;
  value: string | number;
  label: string;
  className?: string;
  onClick?: () => void;
}) {
  const Comp = onClick ? 'button' : 'div';
  return (
    <Comp
      onClick={onClick}
      className={cn(
        'bg-card border border-border rounded-xl p-4 flex items-center gap-4 transition-all',
        onClick && 'cursor-pointer hover:border-venom-yellow/30 hover:shadow-venom text-left',
        className,
      )}
    >
      <div className="w-10 h-10 rounded-lg bg-background flex items-center justify-center shrink-0">
        <Icon className="w-5 h-5 text-venom-yellow" />
      </div>
      <div>
        <p className="text-xl font-semibold text-foreground tabular-nums leading-none mb-1">
          {value}
        </p>
        <p className="text-[11px] text-text-tertiary uppercase tracking-wider">{label}</p>
      </div>
    </Comp>
  );
}
