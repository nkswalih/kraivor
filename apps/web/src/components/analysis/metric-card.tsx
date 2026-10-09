'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

export type CardColor = 'green' | 'orange' | 'blue' | 'red' | 'purple' | 'pink';
export type CardStatus = 'healthy' | 'attention' | 'available' | 'pending';

const BORDER_ACCENT: Record<CardColor, string> = {
  green:  'border-t-green-500/60',
  orange: 'border-t-orange-500/60',
  blue:   'border-t-blue-500/60',
  red:    'border-t-red-500/60',
  purple: 'border-t-purple-500/60',
  pink:   'border-t-pink-500/60',
};

const COLOR_TEXT: Record<CardColor, string> = {
  green:  'text-green-400',
  orange: 'text-orange-400',
  blue:   'text-blue-400',
  red:    'text-red-400',
  purple: 'text-purple-400',
  pink:   'text-pink-400',
};

const STATUS_CONFIG: Record<CardStatus, { label: string; classes: string }> = {
  healthy:   { label: 'Healthy',         classes: 'bg-green-500/10 text-green-400 border-green-500/20' },
  attention: { label: 'Needs Attention', classes: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  available: { label: 'Available',       classes: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  pending:   { label: 'Pending',         classes: 'bg-white/5 text-text-tertiary border-white/10' },
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
    <div className="bg-card border border-border rounded-xl flex flex-col animate-pulse overflow-hidden">
      <div className="h-[3px] shrink-0 bg-surface2" />
      <div className="p-3.5 flex flex-col gap-2.5">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded bg-surface2" />
          <div className="h-5 w-12 rounded bg-surface2" />
          <div className="ml-auto h-3.5 w-14 rounded-full bg-surface2" />
        </div>
        <div className="h-2.5 w-28 rounded bg-surface2" />
        <div className="h-2 w-20 rounded bg-surface2" />
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
  const statusCfg = STATUS_CONFIG[status];
  const Comp = onClick ? 'button' : 'div';

  return (
    <Comp
      onClick={onClick}
      className={cn(
        'bg-card border border-border rounded-xl flex flex-col overflow-hidden',
        'transition-all duration-300 ease-out',
        'hover:shadow-lg hover:border-white/15',
        onClick && 'cursor-pointer text-left w-full',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-venom-yellow/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        'animate-fade-up opacity-0',
        BORDER_ACCENT[color],
        className,
      )}
      style={{ animationDelay: index * 80 + 'ms', animationFillMode: 'forwards' }}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${title}: ${typeof value === 'number' ? value.toLocaleString() : value} - ${statusCfg.label}`}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } } : undefined}
    >
      <div className="p-3.5 flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <Icon className={cn('w-[15px] h-[15px] shrink-0', COLOR_TEXT[color])} />
          <span className="text-lg font-bold text-foreground tabular-nums leading-none tracking-tight">
            {typeof value === 'number' ? <AnimatedValue value={value} /> : value}
          </span>
          <span className={cn('ml-auto px-2 py-0.5 rounded-full border text-[10px] font-medium leading-none', statusCfg.classes)}>
            {statusCfg.label}
          </span>
        </div>
        <p className="text-[12px] font-medium text-foreground leading-tight">{title}</p>
        {subtitle && (
          <p className="text-[10.5px] text-text-tertiary leading-tight">{subtitle}</p>
        )}
      </div>
    </Comp>
  );
}
