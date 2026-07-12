'use client';

import { cn } from '@/lib/utils';
import { RefreshCw, Sparkles } from 'lucide-react';
import { useReEnrich } from '@/lib/hooks/use-analysis';
import { toast } from 'sonner';
import { MarkdownRenderer } from '@/components/ui/markdown/markdown-renderer';

export function AiExecutiveSummarySection({
  summary,
  jobId,
  isLoading,
}: {
  summary: string | null | undefined;
  jobId?: string | null;
  isLoading?: boolean;
}) {
  const reEnrich = useReEnrich();

  const handleRegenerate = () => {
    if (!jobId) return;
    reEnrich.mutate(jobId, {
      onSuccess: () => {
        toast.success('AI enrichment regenerated');
      },
      onError: (err) => {
        toast.error(err.message || 'AI enrichment failed');
      },
    });
  };

  const showSkeleton = isLoading;
  const hasSummary = summary && summary.trim().length > 0;

  if (showSkeleton) {
    return (
      <div className="bg-card border border-border rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-4 h-4 rounded bg-krait-surface2 animate-shimmer" />
          <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-36" />
        </div>
        <div className="space-y-2.5">
          {[100, 92, 80, 72, 88, 65].map((w, i) => (
            <div
              key={i}
              className="h-3 bg-krait-surface2 rounded animate-shimmer"
              style={{ width: `${w}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border">
        <h2 className="text-[13px] font-semibold text-foreground flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-venom-yellow" />
          AI-Powered Analysis
        </h2>
        <div className="flex items-center gap-2">
          {hasSummary && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-venom-yellow/10 text-venom-yellow font-medium uppercase tracking-wider">
              AI-Generated
            </span>
          )}
          {jobId && (
            <button
              onClick={handleRegenerate}
              disabled={reEnrich.isPending}
              className="flex items-center gap-1 px-2 py-1 rounded-md border border-border bg-card text-[11px] text-text-secondary hover:text-foreground hover:border-venom-yellow/30 transition-colors disabled:opacity-50"
              title="Regenerate AI enrichment"
            >
              <RefreshCw
                className={`w-3 h-3 ${reEnrich.isPending ? 'animate-spin' : ''}`}
              />
              {reEnrich.isPending ? 'Generating...' : 'Regenerate'}
            </button>
          )}
        </div>
      </div>
      {hasSummary ? (
        <div className={cn('px-5 py-4')}>
          <MarkdownRenderer content={summary} />
        </div>
      ) : (
        <div className="px-5 py-4 text-[12px] text-text-tertiary">
          AI enrichment is not available. Click <strong>Regenerate</strong> to retry.
        </div>
      )}
    </div>
  );
}
