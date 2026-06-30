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
}: {
  title: string;
  icon: LucideIcon;
  children?: ReactNode;
  className?: string;
  isLoading?: boolean;
  error?: Error | null;
  empty?: boolean;
  emptyMessage?: string;
}) {
  return (
    <div className={cn('bg-card border border-border rounded-xl p-5', className)}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium text-foreground">{title}</h3>
        {isLoading && <Loader2 className="w-3.5 h-3.5 text-venom-yellow animate-spin ml-auto" />}
      </div>

      {isLoading && !children && (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-5 h-5 text-venom-yellow animate-spin" />
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center h-32 gap-2 text-text-tertiary">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span className="text-[12px]">{error.message || 'Failed to load chart data'}</span>
        </div>
      )}

      {empty && !isLoading && !error && (
        <div className="flex flex-col items-center justify-center h-32 gap-1 text-text-tertiary">
          <Icon className="w-5 h-5 opacity-40" />
          <span className="text-[12px]">{emptyMessage || 'No data available'}</span>
        </div>
      )}

      {!isLoading && !error && !empty && children}
    </div>
  );
}
