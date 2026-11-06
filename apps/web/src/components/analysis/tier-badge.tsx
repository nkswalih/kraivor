'use client';

import { Badge } from '@/components/ui/shadcn';
import { Tiers } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';

const VARIANTS: Record<Tiers, { label: string; class: string }> = {
  [Tiers.PRODUCTION_READY]: { label: 'Production Ready', class: 'bg-green-500/20 text-green-400 border-green-500/30' },
  [Tiers.MINOR_ISSUES]: { label: 'Minor Issues', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  [Tiers.NEEDS_WORK]: { label: 'Needs Work', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  [Tiers.SIGNIFICANT_RISK]: { label: 'Significant Risk', class: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  [Tiers.CRITICAL_STATE]: { label: 'Critical State', class: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

export function TierBadge({ tier, className }: { tier: Tiers; className?: string }) {
  const v = VARIANTS[tier] ?? { label: tier, class: '' };
  return (
    <Badge className={cn('border text-[11px] font-medium px-2 py-0.5', v.class, className)}>
      {v.label}
    </Badge>
  );
}
