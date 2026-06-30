'use client';

import { cn } from '@/lib/utils';
import { Loader2, AlertCircle, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

export function ChartCard({
  title,
  icon: Icon,
  children,
  className,
  isLoading,
  error,
  empty,
  emptyMessage,
  headerAction,
}: {
  title: string;
  icon?: LucideIcon;
  children?: ReactNode;
  className?: string;
  isLoading?: boolean;
  error?: Error | null;
  empty?: boolean;
  emptyMessage?: string;
  headerAction?: ReactNode;
}) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-2xl p-5 overflow-hidden',
        'transition-all duration-300 ease-out',
        'hover:border-white/10 hover:shadow-xl hover:bg-card/80',
        className,
      )}
    >
      <div className="flex items-center gap-2 mb-4">
        {Icon && <Icon className="w-4 h-4 text-venom-yellow shrink-0" />}
        <h3 className="text-[13px] font-medium text-foreground">{title}</h3>
        {headerAction && <div className="ml-auto">{headerAction}</div>}
        {isLoading && <Loader2 className="w-3.5 h-3.5 text-venom-yellow animate-spin ml-2" />}
      </div>

      {isLoading && !children && (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-5 h-5 text-venom-yellow animate-spin" />
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center h-40 gap-2 text-text-tertiary">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span className="text-[12px]">{error.message || 'Failed to load chart data'}</span>
        </div>
      )}

      {empty && !isLoading && !error && (
        <div className="flex flex-col items-center justify-center h-40 gap-1 text-text-tertiary">
          {Icon && <Icon className="w-5 h-5 opacity-40" />}
          <span className="text-[12px]">{emptyMessage || 'No data available'}</span>
        </div>
      )}

      {!isLoading && !error && !empty && children}
    </div>
  );
}
