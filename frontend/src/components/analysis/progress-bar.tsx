'use client';

import { cn } from '@/lib/utils';

export function ProgressBar({
  pct,
  message,
  className,
}: {
  pct: number;
  message?: string;
  className?: string;
}) {
  const clamped = Math.min(100, Math.max(0, pct));
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {message && (
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-text-secondary">{message}</span>
          <span className="text-[12px] font-mono text-text-tertiary">{Math.round(clamped)}%</span>
        </div>
      )}
      <div className="h-1.5 bg-krait-surface2 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${clamped}%`,
            background: 'linear-gradient(90deg, #eab308, #f59e0b)',
          }}
        />
      </div>
    </div>
  );
}
