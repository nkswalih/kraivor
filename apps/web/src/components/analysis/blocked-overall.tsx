'use client';

import { ShieldOff, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const ENGINE_BLOCK_LABELS: Record<string, string> = {
  security: 'Security Engine',
  reliability: 'Reliability Engine',
  maintainability: 'Maintainability Engine',
  devops: 'DevOps Engine',
  performance: 'Performance Engine',
};

function getReason(block: string): string {
  if (block.includes(':')) {
    const [engine, ...rest] = block.split(':');
    const reason = rest.join(':').trim();
    const label = ENGINE_BLOCK_LABELS[engine.trim()] ?? engine.trim();
    return `${label}: ${reason}`;
  }
  return ENGINE_BLOCK_LABELS[block] ?? block;
}

const SEVERITY_BLOCK = new Set(['maintainability', 'security']);

export function BlockedOverall({
  blockedBy,
  className,
  onDismiss,
}: {
  blockedBy: string[];
  className?: string;
  onDismiss?: () => void;
}) {
  if (!blockedBy.length) return null;

  const isSevere = blockedBy.some(b => SEVERITY_BLOCK.has(b.trim().split(':')[0]));

  return (
    <div
      className={cn(
        'relative rounded-lg border p-4 flex items-start gap-3',
        isSevere
          ? 'border-red-500/30 bg-red-500/10'
          : 'border-yellow-500/30 bg-yellow-500/10',
        className,
      )}
    >
      <ShieldOff
        className={cn(
          'w-5 h-5 shrink-0 mt-0.5',
          isSevere ? 'text-red-400' : 'text-yellow-400',
        )}
      />
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-[13px] font-medium',
            isSevere ? 'text-red-400' : 'text-yellow-400',
          )}
        >
          Score Blocked
        </p>
        <p className="text-[12px] text-text-tertiary mt-1">
          {isSevere
            ? 'Core engines failed or were not configured. Overall score cannot be calculated until the following issues are resolved:'
            : 'Some engines did not complete. Overall score reflects only available data:'}
        </p>
        <ul className="mt-2 space-y-1">
          {blockedBy.map((block, i) => (
            <li key={i} className="flex items-start gap-2 text-[12px] text-text-secondary">
              <span className="w-1 h-1 rounded-full bg-current mt-1.5 shrink-0" />
              <span>{getReason(block)}</span>
            </li>
          ))}
        </ul>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 rounded hover:bg-white/5 text-text-tertiary hover:text-text-primary transition-colors shrink-0"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
