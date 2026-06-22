'use client';

import { SignalHigh, SignalMedium, SignalLow } from 'lucide-react';
import type { TaskPriority } from '@/types/domain/projects';

const CONFIG: Record<TaskPriority, { Icon: typeof SignalHigh; className: string }> = {
  critical: { Icon: SignalHigh, className: 'text-[var(--venom-orange)]' },
  high: { Icon: SignalHigh, className: 'text-[var(--venom-yellow)]' },
  medium: { Icon: SignalMedium, className: 'text-[var(--text-secondary)]' },
  low: { Icon: SignalLow, className: 'text-[var(--text-tertiary)]' },
};

interface PriorityIconProps {
  priority: TaskPriority;
  size?: number;
}

export function PriorityIcon({ priority, size = 14 }: PriorityIconProps) {
  const { Icon, className } = CONFIG[priority];
  return <Icon size={size} className={className} />;
}
