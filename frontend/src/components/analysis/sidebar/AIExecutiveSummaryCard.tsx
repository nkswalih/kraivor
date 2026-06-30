'use client';

import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { aiApi, type EnrichResponse } from '@/lib/api/ai-api';
import type { AiSummaryCard, Finding, Report } from '@/types/domain/analysis';
import { Sparkles } from 'lucide-react';

export function AIExecutiveSummaryCard({
  data,
  findings,
  report,
  jobId,
  isLoading,
  className,
}: {
  data: AiSummaryCard;
  findings: Finding[] | null | undefined;
  report: Report | null | undefined;
  jobId: string | null;
  isLoading?: boolean;
  className?: string;
}) {
  const hasFindings = findings && findings.length > 0 && jobId;

  const { data: enrichment, isLoading: isEnriching } = useQuery<EnrichResponse>({
    queryKey: ['ai-enrichment', jobId],
    queryFn: () =>
      aiApi.enrichAnalysis({
        findings: (findings ?? []).map(f => ({
          title: f.title,
          category: f.category,
          severity: f.severity,
          description: f.description,
          recommendation: f.recommendation,
          file_path: f.file_path ?? '',
          line_start: f.line_start,
          line_end: f.line_end,
          code_snippet: f.code_snippet ?? '',
        })),
        overall_score: report?.overall_score ?? null,
        tier: null,
        languages: report?.languages_detected ?? null,
        frameworks: null,
      }),
    enabled: !!hasFindings,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const summary = enrichment?.ai_executive_summary ?? data.summary;
  const isAiGenerated = enrichment?.ai_executive_summary ? true : data.isAiGenerated;
  const busy = isLoading || isEnriching;

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-foreground flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-venom-yellow" />
          AI Executive Summary
        </h3>
        {!isAiGenerated && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-venom-yellow/10 text-venom-yellow font-medium uppercase tracking-wider">
            Preview
          </span>
        )}
      </div>

      {busy ? (
        <div className="space-y-2">
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer" />
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-11/12" />
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-4/5" />
          <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-3/4" />
        </div>
      ) : (
        <div className="text-[12px] text-text-secondary leading-relaxed whitespace-pre-wrap">
          {summary}
        </div>
      )}

      {!isAiGenerated && !busy && (
        <p className="mt-3 text-[10px] text-text-tertiary italic border-t border-border pt-3">
          Static preview — AI summary will appear after analysis completes.
        </p>
      )}
    </div>
  );
}
