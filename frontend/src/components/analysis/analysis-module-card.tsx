'use client';

import { cn } from '@/lib/utils';
import { ArrowRight, type LucideIcon } from 'lucide-react';
import Link from 'next/link';

export type ModuleColor = 'green' | 'orange' | 'blue' | 'red' | 'purple' | 'pink';

const MODULE_COLORS: Record<ModuleColor, { container: string; icon: string; glow: string }> = {
  green: { container: 'bg-green-500/10', icon: 'text-green-400', glow: 'rgba(74,222,128,0.15)' },
  orange: { container: 'bg-orange-500/10', icon: 'text-orange-400', glow: 'rgba(251,146,60,0.15)' },
  blue: { container: 'bg-blue-500/10', icon: 'text-blue-400', glow: 'rgba(96,165,250,0.15)' },
  red: { container: 'bg-red-500/10', icon: 'text-red-400', glow: 'rgba(248,113,113,0.15)' },
  purple: { container: 'bg-purple-500/10', icon: 'text-purple-400', glow: 'rgba(192,132,252,0.15)' },
  pink: { container: 'bg-pink-500/10', icon: 'text-pink-400', glow: 'rgba(236,72,153,0.15)' },
};

function ModuleCardStat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <span className="flex items-center gap-1.5 text-[13px]">
      {color && <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />}
      <span className="tabular-nums font-medium text-foreground">{value}</span>
      <span className="text-text-tertiary font-normal">{label}</span>
    </span>
  );
}

export function AnalysisModuleCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-6 h-[162px] flex flex-col animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-surface2 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-5 w-28 rounded bg-surface2" />
          <div className="h-4 w-20 rounded bg-surface2" />
        </div>
      </div>
      <div className="flex-1 mt-3">
        <div className="h-4 w-3/4 rounded bg-surface2" />
        <div className="h-4 w-1/2 rounded bg-surface2 mt-1.5" />
      </div>
      <div className="flex items-center justify-between mt-auto pt-3">
        <div className="flex gap-3">
          <div className="h-4 w-16 rounded bg-surface2" />
          <div className="h-4 w-16 rounded bg-surface2" />
          <div className="h-4 w-16 rounded bg-surface2" />
        </div>
        <div className="h-5 w-28 rounded bg-surface2" />
      </div>
    </div>
  );
}

export function AnalysisModuleCard({
  href,
  icon: Icon,
  title,
  count,
  description,
  stats,
  color,
  actionLabel,
  index = 0,
  className,
}: {
  href: string;
  icon: LucideIcon;
  title: string;
  count?: string;
  description: string;
  stats?: { label: string; value: string | number; color?: string }[];
  color: ModuleColor;
  actionLabel: string;
  index?: number;
  className?: string;
}) {
  const colors = MODULE_COLORS[color];

  return (
    <Link
      href={href}
      className={cn(
        'group bg-card border border-border rounded-2xl p-6 h-[162px] flex flex-col',
        'transition-all duration-300 ease-out',
        'hover:-translate-y-1 hover:shadow-xl hover:border-white/10',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-venom-yellow/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        'animate-fade-up opacity-0',
        className,
      )}
      style={{ animationDelay: index * 80 + 'ms', animationFillMode: 'forwards' }}
      aria-label={title + ': ' + description}
    >
      <div className="flex items-start gap-4">
        <div
          className={cn('w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-300 group-hover:rotate-[-8deg]', colors.container)}
          style={{ boxShadow: '0 0 10px ' + colors.glow }}
        >
          <Icon className={cn('w-5 h-5', colors.icon)} />
        </div>
        <div className="min-w-0">
          <h4 className="text-[18px] font-bold text-foreground leading-tight tracking-tight">{title}</h4>
          {count && <p className="text-[14px] text-text-secondary font-medium mt-0.5">{count}</p>}
        </div>
      </div>

      <p className="text-[13px] text-text-tertiary mt-2 leading-relaxed line-clamp-2">{description}</p>

      <div className="flex items-end justify-between mt-auto pt-3">
        {stats && stats.length > 0 ? (
          <div className="flex items-center gap-3 flex-wrap min-w-0">
            {stats.map(stat => (
              <ModuleCardStat key={stat.label} label={stat.label} value={stat.value} color={stat.color} />
            ))}
          </div>
        ) : (
          <div />
        )}
        <span className="flex items-center gap-1.5 text-[14px] font-semibold text-venom-yellow shrink-0 transition-all duration-300 group-hover:gap-2.5">
          {actionLabel}
          <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}
