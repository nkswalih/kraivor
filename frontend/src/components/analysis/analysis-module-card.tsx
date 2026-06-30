'use client';

import { cn } from '@/lib/utils';
import { ChevronRight, type LucideIcon } from 'lucide-react';
import Link from 'next/link';

export function AnalysisModuleCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-xl p-5 animate-fade-up">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-24 rounded bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
          <div className="h-3 w-32 rounded bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
        </div>
      </div>
    </div>
  );
}

export function AnalysisModuleCard({
  href,
  icon: Icon,
  label,
  count,
  countLabel,
  iconColor,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
  count?: number | string;
  countLabel?: string;
  iconColor?: string;
}) {
  return (
    <Link
      href={href}
      className="group bg-card border border-border rounded-xl p-5 flex items-center gap-4 transition-all hover:border-venom-yellow/30 hover:shadow-venom"
    >
      <div className={cn(
        'w-10 h-10 rounded-lg bg-background flex items-center justify-center shrink-0 transition-colors group-hover:bg-venom-yellow/10',
      )}>
        <Icon
          className="w-5 h-5 transition-colors group-hover:text-venom-yellow"
          style={{ color: iconColor ?? 'hsl(var(--text-tertiary))' }}
        />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-foreground group-hover:text-venom-yellow transition-colors truncate">
          {label}
        </p>
        {count != null && (
          <p className="text-[11px] text-text-tertiary mt-0.5">
            {count}{countLabel ? ` ${countLabel}` : ''}
          </p>
        )}
      </div>

      <ChevronRight className="w-4 h-4 text-text-tertiary group-hover:text-venom-yellow transition-colors shrink-0" />
    </Link>
  );
}
