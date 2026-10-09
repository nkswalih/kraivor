'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Bug, AlertCircle, FileCode } from 'lucide-react';
import { useDeadCode } from '@/lib/hooks/use-analysis';
import { Badge, Skeleton } from '@/components/ui/shadcn';
import { DeadCodeType } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';
import type { DeadCodeFinding } from '@/types/domain/analysis';

const DEAD_CODE_TABS = [
  { value: '', label: 'All' },
  { value: DeadCodeType.UNUSED_IMPORT, label: 'Unused Imports' },
  { value: DeadCodeType.UNUSED_FUNCTION, label: 'Unused Functions' },
  { value: DeadCodeType.UNUSED_VARIABLE, label: 'Unused Variables' },
  { value: DeadCodeType.ORPHAN_CLASS, label: 'Orphan Classes' },
  { value: DeadCodeType.UNREACHABLE_CODE, label: 'Unreachable Code' },
];

function confidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'bg-green-500';
  if (confidence >= 0.75) return 'bg-yellow-500';
  return 'bg-orange-500';
}

export default function DeadCodePage() {
  const params = useParams<{ workspace: string; jobId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';

  const { data, isLoading, error } = useDeadCode(jobId);
  const [filter, setFilter] = useState('');

  const findings = (data?.findings ?? []) as DeadCodeFinding[];
  const filtered = filter ? findings.filter((f) => f.code_type === filter) : findings;

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center gap-3 mb-3">
          <Link
            href={`/${workspaceSlug}/analysis/jobs/${jobId}`}
            className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground flex items-center gap-2">
            <Bug className="w-5 h-5 text-orange-400" /> Dead Code
          </h1>
          {!isLoading && <span className="text-[12px] text-text-tertiary">({data?.total ?? 0} instances)</span>}
        </div>

        <div className="flex items-center gap-1 bg-card border border-border p-1 rounded-lg w-fit">
          {DEAD_CODE_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setFilter(tab.value)}
              className={cn(
                'px-3 py-1.5 text-[12px] font-medium rounded-md transition-all',
                filter === tab.value
                  ? 'bg-background border border-border text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {error ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <AlertCircle className="w-10 h-10 text-color-error mb-3" />
            <p className="text-base font-medium text-text-primary mb-1">Failed to load dead code findings</p>
            <p className="text-sm text-text-tertiary">{error.message}</p>
          </div>
        ) : isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} variant="rect" className="h-32" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Bug className="w-10 h-10 text-text-tertiary mb-3" />
            <p className="text-base font-medium text-text-primary mb-1">No dead code found</p>
            <p className="text-sm text-text-tertiary">All code appears to be in use</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filtered.map((f) => (
              <div key={f.id} className="border border-border rounded-lg bg-card p-4 hover:border-venom-yellow/30 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 text-[11px]">
                    {f.code_type.replace(/_/g, ' ')}
                  </Badge>
                  <div className="flex items-center gap-1">
                    <div className={cn('w-2 h-2 rounded-full', confidenceColor(f.confidence))} />
                    <span className="text-[11px] text-text-tertiary font-mono">
                      {Math.round(f.confidence * 100)}%
                    </span>
                  </div>
                </div>
                <p className="text-[13px] font-medium text-foreground mb-1">{f.name}</p>
                <p className="text-[12px] text-text-tertiary flex items-center gap-1">
                  <FileCode className="w-3 h-3" />
                  {f.file_path}
                  {f.line_start != null && `:${f.line_start}`}
                </p>
                {f.context && <p className="text-[12px] text-text-tertiary mt-2">{f.context}</p>}
                {f.evidence && (
                  <p className="text-[11px] text-text-tertiary mt-1 italic">Evidence: {f.evidence}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
