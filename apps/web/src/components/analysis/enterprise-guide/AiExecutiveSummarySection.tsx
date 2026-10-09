'use client';

import { cn } from '@/lib/utils';
import { RefreshCw, Sparkles } from 'lucide-react';
import { useReEnrich } from '@/lib/hooks/use-analysis';
import { toast } from 'sonner';
import { MarkdownRenderer } from '@/components/ui/markdown/markdown-renderer';
import { AiSummaryErrorPanel } from '@/components/analysis/ai-summary/AiSummaryErrorPanel';
import type { AiSummaryError } from '@/types/domain/analysis';

export function AiExecutiveSummarySection({
  summary,
  error,
  jobId,
  isLoading,
}: {
  summary: string | null | undefined;
  /**
   * Why the summary is missing, or -- when one is present -- why the *last*
   * regeneration of it failed.
   *
   * The second reading is the reason this is a separate prop rather than
   * something derived from `summary`. A re-enrich that fails deliberately keeps
   * the previous summary: a paying user should not lose one because a regenerate
   * did not work. So a summary and a reason can arrive together, and the pair
   * means "this is the last one that worked", which is a different thing from
   * either alone and cannot be rendered as either.
   */
  error?: AiSummaryError | null;
  jobId?: string | null;
  isLoading?: boolean;
}) {
  const reEnrich = useReEnrich();

  const handleRegenerate = () => {
    if (!jobId) return;
    reEnrich.mutate(jobId, {
      // Branched on `status` rather than reporting arrival as success. The
      // endpoint returns 200 either way -- a re-enrich that reached the provider
      // and was refused has genuinely succeeded at the HTTP level -- so
      // `onSuccess` fired for both and toasted "AI enrichment regenerated" over a
      // run that still had no summary. `status: "degraded"` is the service saying
      // so, and it is the only thing here that knows.
      onSuccess: (result) => {
        if (result.status === 'ok') {
          toast.success('AI enrichment regenerated');
          return;
        }
        // The detail is already on screen by the time this fires: the hook
        // invalidates `analysis-guide`, the guide re-reads, and the panel
        // renders `result.ai_summary_error`. The toast only has to say the retry
        // did not work, and not say why -- repeating the reason in a toast that
        // disappears would be the second copy of the same sentence.
        toast.error(
          result.ai_summary_error?.message ??
            'The AI summary could not be generated. The findings were still enriched.'
        );
      },
      onError: (err) => {
        toast.error(err.message || 'AI enrichment failed');
      },
    });
  };

  const hasSummary = Boolean(summary && summary.trim().length > 0);
  // A summary that is present but has a reason beside it is stale. Labelled as
  // such rather than hidden: hiding it would lose the work that did succeed, and
  // showing it unlabelled would let a reader treat a summary the service has
  // already said it could not refresh as current.
  const summaryIsStale = hasSummary && Boolean(error);

  // Early return, unchanged in shape from before this task. Restructured once
  // while adding the error states, and reverted: the alternative renders the
  // header -- and so the Regenerate button -- while the guide is still loading,
  // which is both a layout jump and a button that can be pressed before there is
  // anything to regenerate.
  if (isLoading) {
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
              {summaryIsStale ? 'Stale — last attempt failed' : 'AI-Generated'}
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
                aria-hidden="true"
                className={cn(
                  'w-3 h-3',
                  reEnrich.isPending && 'animate-spin motion-reduce:animate-none',
                )}
              />
              {reEnrich.isPending ? 'Generating...' : 'Regenerate'}
            </button>
          )}
        </div>
      </div>

      {/* The reason sits above the body rather than replacing it, and is the
          only thing rendered when there is no summary. Rendering it in both
          positions is deliberate: a stale summary needs the reason attached to
          it, and an absent one needs no other content at all. */}
      {error && (
        <div className="px-5 pt-4 pb-1">
          <AiSummaryErrorPanel
            error={error}
            onRetry={jobId ? handleRegenerate : undefined}
            isRetrying={reEnrich.isPending}
          />
        </div>
      )}

      {hasSummary ? (
        <div className={cn('px-5 py-4', error && 'pt-3')}>
          <MarkdownRenderer content={summary} />
        </div>
      ) : (
        !error && (
          /* Only when there is genuinely nothing: no summary and no recorded
             reason means the stage never ran, which is the one case where
             "not available, click Regenerate" is the accurate sentence. It was
             previously the only sentence, and it was shown for all four. */
          <div className="px-5 py-4 text-[12px] text-text-tertiary">
            AI enrichment is not available. Click <strong>Regenerate</strong> to
            retry.
          </div>
        )
      )}
    </div>
  );
}
