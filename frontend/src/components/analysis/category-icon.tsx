'use client';

import {
  Shield,
  Zap,
  Server,
  Activity,
  Code,
  Bug,
  AlertTriangle,
  Layout,
  Star,
  type LucideIcon,
} from 'lucide-react';
import { Category } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';

const ICONS: Record<string, LucideIcon> = {
  [Category.SECURITY]: Shield,
  [Category.PERFORMANCE]: Zap,
  [Category.RELIABILITY]: Server,
  [Category.MAINTAINABILITY]: Code,
  [Category.DEVOPS]: Activity,
  [Category.DEAD_CODE]: Bug,
  [Category.ERROR]: AlertTriangle,
  [Category.STRUCTURE]: Layout,
  [Category.QUALITY]: Star,
};

const COLORS: Record<string, string> = {
  [Category.SECURITY]: 'text-red-400',
  [Category.PERFORMANCE]: 'text-yellow-400',
  [Category.RELIABILITY]: 'text-blue-400',
  [Category.MAINTAINABILITY]: 'text-purple-400',
  [Category.DEVOPS]: 'text-green-400',
  [Category.DEAD_CODE]: 'text-orange-400',
  [Category.ERROR]: 'text-red-500',
  [Category.STRUCTURE]: 'text-cyan-400',
  [Category.QUALITY]: 'text-pink-400',
};

export function CategoryIcon({
  category,
  className,
}: {
  category: string;
  className?: string;
}) {
  const Icon = ICONS[category] ?? Activity;
  return <Icon className={cn('w-4 h-4', COLORS[category], className)} />;
}
