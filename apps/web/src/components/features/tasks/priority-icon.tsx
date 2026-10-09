'use client';

import { SignalHigh, SignalMedium, SignalLow } from 'lucide-react';
import type { TaskPriority } from '@/types/domain/projects';

const CONFIG: Record<TaskPriority, { Icon: typeof SignalHigh; className: string }> = {
  critical: { Icon: SignalHigh, className: 'text-red-500' },
  high: { Icon: SignalHigh, className: 'text-orange-500' },
  medium: { Icon: SignalMedium, className: 'text-yellow-500' },
  low: { Icon: SignalLow, className: 'text-green-500' },
};

interface PriorityIconProps {
  priority: TaskPriority;
  size?: number;
}

export function PriorityIcon({ priority, size = 14 }: PriorityIconProps) {
  const { Icon, className } = CONFIG[priority];
  return <Icon size={size} className={className} />;
}
