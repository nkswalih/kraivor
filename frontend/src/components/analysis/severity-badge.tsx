'use client';

import { Badge } from '@/components/ui/shadcn';
import { Severity } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';

const VARIANTS: Record<Severity, { label: string; class: string }> = {
  [Severity.CRITICAL]: { label: 'Critical', class: 'bg-red-500/20 text-red-400 border-red-500/30' },
  [Severity.HIGH]: { label: 'High', class: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  [Severity.MEDIUM]: { label: 'Medium', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  [Severity.LOW]: { label: 'Low', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  [Severity.INFO]: { label: 'Info', class: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
};

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const v = VARIANTS[severity] ?? { label: severity, class: '' };
  return (
    <Badge className={cn('border text-[11px] font-medium px-2 py-0.5', v.class, className)}>
      {v.label}
    </Badge>
  );
}
