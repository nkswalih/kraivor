'use client';

import { Badge } from '@/components/ui/shadcn';
import { JobStatus } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';

const VARIANTS: Record<JobStatus, { label: string; class: string }> = {
  [JobStatus.QUEUED]: { label: 'Queued', class: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
  [JobStatus.CLONING]: { label: 'Cloning', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  [JobStatus.PARSING]: { label: 'Parsing', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  [JobStatus.RULES]: { label: 'Rules', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  [JobStatus.DEAD_CODE]: { label: 'Dead Code', class: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  [JobStatus.ERRORS]: { label: 'Errors', class: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  [JobStatus.PERF]: { label: 'Perf', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  [JobStatus.SIMULATION]: { label: 'Simulation', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  [JobStatus.SCORING]: { label: 'Scoring', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  [JobStatus.GUIDE_GEN]: { label: 'Guide', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  [JobStatus.COMPLETED]: { label: 'Completed', class: 'bg-green-500/20 text-green-400 border-green-500/30' },
  [JobStatus.FAILED]: { label: 'Failed', class: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

export function JobStatusBadge({ status, className }: { status: JobStatus; className?: string }) {
  const v = VARIANTS[status] ?? { label: status, class: '' };
  return (
    <Badge className={cn('border text-[11px] font-medium px-2 py-0.5', v.class, className)}>
      {v.label}
    </Badge>
  );
}
