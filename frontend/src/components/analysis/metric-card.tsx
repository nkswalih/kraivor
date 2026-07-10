'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

export type CardColor = 'green' | 'orange' | 'blue' | 'red' | 'purple' | 'pink';
export type CardStatus = 'healthy' | 'attention' | 'available' | 'pending';

const COLOR_MAP: Record<CardColor, { container: string; icon: string; glow: string }> = {
  green: { container: 'bg-green-500/10', icon: 'text-green-400', glow: 'rgba(74,222,128,0.2)' },
  orange: { container: 'bg-orange-500/10', icon: 'text-orange-400', glow: 'rgba(251,146,60,0.2)' },
  blue: { container: 'bg-blue-500/10', icon: 'text-blue-400', glow: 'rgba(96,165,250,0.2)' },
  red: { container: 'bg-red-500/10', icon: 'text-red-400', glow: 'rgba(248,113,113,0.2)' },
  purple: { container: 'bg-purple-500/10', icon: 'text-purple-400', glow: 'rgba(192,132,252,0.2)' },
  pink: { container: 'bg-pink-500/10', icon: 'text-pink-400', glow: 'rgba(236,72,153,0.2)' },
};

const STATUS_CONFIG: Record<CardStatus, { label: string; classes: string }> = {
  healthy: { label: 'Healthy', classes: 'bg-green-500/10 text-green-400 border-green-500/20' },
  attention: { label: 'Needs Attention', classes: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  available: { label: 'Available', classes: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  pending: { label: 'Pending', classes: 'bg-white/5 text-text-tertiary border-white/10' },
};

function AnimatedValue({ value: target, duration = 400 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(target);
  const prevRef = useRef(target);

  useEffect(() => {
    const start = prevRef.current;
    prevRef.current = target;
    if (start === target) { setDisplay(target); return; }
    const startTime = performance.now();
    const raf = requestAnimationFrame(function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(start + (target - start) * eased));
      if (progress < 1) requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return <>{display}</>;
}

export function MetricCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-4 flex flex-col animate-pulse aspect-square">
      <div className="flex items-start justify-between">
        <div className="w-9 h-9 rounded-xl bg-surface2" />
        <div className="h-4 w-16 rounded-full bg-surface2" />
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="h-7 w-12 rounded bg-surface2" />
      </div>
      <div className="space-y-1">
        <div className="h-3 w-16 rounded bg-surface2" />
        <div className="h-2.5 w-12 rounded bg-surface2" />
      </div>
    </div>
  );
}

export function MetricCard({
  icon: Icon,
  value,
  title,
  subtitle,
  status,
  color,
  index = 0,
  onClick,
  className,
}: {
  icon: LucideIcon;
  value: number | string;
  title: string;
  subtitle?: string;
  status: CardStatus;
  color: CardColor;
  index?: number;
  onClick?: () => void;
  className?: string;
}) {
  const colors = COLOR_MAP[color];
  const statusCfg = STATUS_CONFIG[status];
  const Comp = onClick ? 'button' : 'div';

  return (
    <Comp
      onClick={onClick}
      className={cn(
        'bg-card border border-border rounded-2xl p-4 flex flex-col gap-2',
        'transition-all duration-300 ease-out',
        'hover:-translate-y-0.5 hover:shadow-lg hover:border-white/10',
        onClick && 'cursor-pointer text-left w-full',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-venom-yellow/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        'animate-fade-up opacity-0',
        className,
      )}
      style={{ animationDelay: index * 80 + 'ms', animationFillMode: 'forwards' }}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${title}: ${typeof value === 'number' ? value.toLocaleString() : value} - ${statusCfg.label}`}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } } : undefined}
    >
      <div className="flex items-start justify-between gap-1">
        <div
          className={cn('w-9 h-9 rounded-xl flex items-center justify-center shrink-0', colors.container)}
          style={{ boxShadow: '0 0 8px ' + colors.glow }}
        >
          <Icon className={cn('w-[18px] h-[18px]', colors.icon)} />
        </div>
        <span className={cn('px-2 py-0.5 rounded-full border text-[10px] font-medium leading-none', statusCfg.classes)}>
          {statusCfg.label}
        </span>
      </div>

      <div className="flex-1 flex items-center justify-center">
        <span className="text-[24px] font-bold text-foreground tabular-nums leading-none tracking-tight">
          {typeof value === 'number' ? <AnimatedValue value={value} /> : value}
        </span>
      </div>

      <div className="text-center">
        <p className="text-[11px] font-medium text-foreground leading-tight">{title}</p>
        {subtitle && (
          <p className="text-[10px] text-text-tertiary mt-0.5 leading-tight">{subtitle}</p>
        )}
      </div>
    </Comp>
  );
}
