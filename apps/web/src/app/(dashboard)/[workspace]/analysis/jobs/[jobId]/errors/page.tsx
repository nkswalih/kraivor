'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, AlertTriangle, AlertCircle, FileCode } from 'lucide-react';
import { useErrorFindings } from '@/lib/hooks/use-analysis';
import { SeverityBadge } from '@/components/analysis/severity-badge';
import { Badge, Skeleton } from '@/components/ui/shadcn';
import { ErrorType } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';
import type { ErrorFinding } from '@/types/domain/analysis';

const ERROR_TABS = [
  { value: '', label: 'All' },
  { value: ErrorType.BARE_EXCEPT, label: 'Bare Except' },
  { value: ErrorType.SWALLOWED_EXCEPTION, label: 'Swallowed Exceptions' },
  { value: ErrorType.MISSING_TIMEOUT, label: 'Missing Timeouts' },
  { value: ErrorType.SILENT_FAIL, label: 'Silent Failures' },
];

export default function ErrorFindingsPage() {
  const params = useParams<{ workspace: string; jobId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';

  const { data, isLoading, error } = useErrorFindings(jobId);
  const [filter, setFilter] = useState('');

  const findings = (data?.findings ?? []) as ErrorFinding[];
  const filtered = filter ? findings.filter((f) => f.error_type === filter) : findings;

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
            <AlertTriangle className="w-5 h-5 text-red-400" /> Error Patterns
          </h1>
          {!isLoading && <span className="text-[12px] text-text-tertiary">({data?.total ?? 0} issues)</span>}
        </div>

        <div className="flex items-center gap-1 bg-card border border-border p-1 rounded-lg w-fit">
          {ERROR_TABS.map((tab) => (
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
            <p className="text-base font-medium text-text-primary mb-1">Failed to load error findings</p>
            <p className="text-sm text-text-tertiary">{error.message}</p>
          </div>
        ) : isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} variant="rect" className="h-28" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <AlertTriangle className="w-10 h-10 text-text-tertiary mb-3" />
            <p className="text-base font-medium text-text-primary mb-1">No error patterns found</p>
            <p className="text-sm text-text-tertiary">Error handling looks solid</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((f) => (
              <div key={f.id} className="border border-border rounded-lg bg-card p-4 hover:border-venom-yellow/30 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <Badge className="bg-orange-500/20 text-orange-400 border-orange-500/30 text-[11px]">
                      {f.error_type.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                </div>
                <p className="text-[13px] font-medium text-foreground mb-1">{f.title}</p>
                {f.description && <p className="text-[12px] text-text-tertiary mb-2">{f.description}</p>}
                <p className="text-[12px] text-text-tertiary flex items-center gap-1">
                  <FileCode className="w-3 h-3" />
                  {f.file_path}
                  {f.line_start != null && `:${f.line_start}`}
                </p>
                {f.code_snippet && (
                  <pre className="mt-2 bg-krait-surface2 border border-border rounded-md p-3 text-[12px] font-mono text-foreground overflow-x-auto">
                    {f.code_snippet}
                  </pre>
                )}
                {f.recommendation && (
                  <p className="text-[12px] text-green-400 mt-2">Recommendation: {f.recommendation}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
