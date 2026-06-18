'use client';

import type { TaskStatus } from '@/types/domain/projects';

interface StatusIconProps {
  status: TaskStatus;
  size?: number;
}

export function StatusIcon({ status, size = 14 }: StatusIconProps) {
  const configs: Record<TaskStatus, { className: string; inner?: string }> = {
    backlog:     { className: 'border border-dashed border-[var(--krait-border-hi)]' },
    todo:        { className: 'border-2 border-[var(--text-tertiary)]' },
    in_progress: { className: 'border-2 border-[var(--venom-amber)]', inner: 'bg-[var(--venom-amber)]' },
    in_review:   { className: 'border-2 border-[var(--color-info)]', inner: 'bg-[var(--color-info)]' },
    blocked:     { className: 'border-2 border-[var(--color-error)] bg-[var(--color-error)]/20' },
    done:        { className: 'bg-[var(--color-success)]' },
    cancelled:   { className: 'border border-[var(--text-tertiary)] bg-[var(--text-tertiary)]/30' },
  };

  const { className, inner } = configs[status];

  return (
    <div
      style={{ width: size, height: size }}
      className={`rounded-full flex items-center justify-center shrink-0 ${className}`}
    >
      {inner && (
        <div
          style={{ width: size * 0.4, height: size * 0.4 }}
          className={`rounded-full ${inner}`}
        />
      )}
    </div>
  );
}
