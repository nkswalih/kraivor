'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, FileText, RefreshCw, ChevronRight, ChevronDown, AlertCircle, Users, Zap, Gauge, Layers, Route, Shield } from 'lucide-react';
import { useEnterpriseGuide } from '@/lib/hooks/use-analysis';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { AiExecutiveSummarySection } from '@/components/analysis/enterprise-guide/AiExecutiveSummarySection';
import { PriorityRecommendationSection } from '@/components/analysis/enterprise-guide/PriorityRecommendationSection';

function AccordionSection({
  title,
  count,
  severity,
  children,
  defaultOpen = false,
}: {
  title: string;
  count: number;
  severity: 'critical' | 'high' | 'medium';
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const dotColor = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
  }[severity];

  return (
    <div className="border border-border rounded-lg bg-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors text-left group"
      >
        <div className="flex items-center gap-2.5">
          <div className={cn('w-1.5 h-1.5 rounded-full', dotColor)} />
          <span className="text-[13px] font-medium text-foreground">{title}</span>
          <span className="text-[11px] text-text-tertiary bg-krait-surface2 px-2 py-0.5 rounded-full tabular-nums">{count}</span>
        </div>
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-text-tertiary group-hover:text-foreground transition-colors" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-text-tertiary group-hover:text-foreground transition-colors" />
        )}
      </button>
      {open && <div className="border-t border-border px-4 py-3 space-y-2">{children}</div>}
    </div>
  );
}

function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

function IssueCard({
  issue,
  severity,
}: {
  issue: Record<string, string>;
  severity: 'critical' | 'high' | 'medium';
}) {
  const borderColor = {
    critical: 'border-red-500/20',
    high: 'border-orange-500/20',
    medium: 'border-yellow-500/20',
  }[severity];

  const bgColor = {
    critical: 'bg-red-500/[0.03]',
    high: 'bg-orange-500/[0.03]',
    medium: 'bg-yellow-500/[0.03]',
  }[severity];

  return (
    <div className={cn('border rounded-lg p-3', borderColor, bgColor)}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-[13px] font-medium text-foreground">{issue.title}</p>
      </div>
      {issue.file_path && (
        <p className="text-[11px] font-mono text-text-secondary mt-1 truncate" title={issue.file_path}>
          {issue.file_path}
        </p>
      )}
      {issue.description && (
        <p className="text-[12px] text-text-secondary mt-2 leading-relaxed">{issue.description}</p>
      )}
      {issue.recommendation && (
        <div className="mt-2 pt-2 border-t border-border/50">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary mb-0.5">Fix</p>
          <p className="text-[12px] text-foreground leading-relaxed">{issue.recommendation}</p>
        </div>
      )}
    </div>
  );
}

export default function EnterpriseGuidePage() {
  const params = useParams<{ workspace: string; jobId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';

  const queryClient = useQueryClient();
  const { data: guide, isLoading, error } = useEnterpriseGuide(jobId);
  const [regenerating, setRegenerating] = useState(false);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await queryClient.invalidateQueries({ queryKey: ['analysis-guide', jobId] });
      toast.success('Guide refreshed');
    } catch {
      toast.error('Failed to refresh guide');
    } finally {
      setRegenerating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col h-full animate-fade-up">
        <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-krait-surface2 animate-shimmer" />
            <div className="h-5 bg-krait-surface2 animate-shimmer w-36 rounded" />
            <div className="ml-auto h-7 bg-krait-surface2 animate-shimmer w-24 rounded" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto w-full space-y-5">
          <div className="bg-card border border-border rounded-lg p-5 space-y-3">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-4 h-4 rounded bg-krait-surface2 animate-shimmer" />
              <div className="h-4 bg-krait-surface2 animate-shimmer w-32 rounded" />
            </div>
            <div className="h-3 bg-krait-surface2 animate-shimmer w-full rounded" />
            <div className="h-3 bg-krait-surface2 animate-shimmer w-11/12 rounded" />
            <div className="h-3 bg-krait-surface2 animate-shimmer w-4/5 rounded" />
          </div>
          <div className="bg-card border border-border rounded-lg p-5 space-y-3">
            <div className="h-4 bg-krait-surface2 animate-shimmer w-44 rounded" />
            <div className="space-y-2">
              <div className="h-3 bg-krait-surface2 animate-shimmer w-3/4 rounded" />
              <div className="h-3 bg-krait-surface2 animate-shimmer w-full rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !guide) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <AlertCircle className="w-10 h-10 text-color-error mb-3" />
        <p className="text-base font-medium text-text-primary mb-1">Guide not found</p>
        <p className="text-sm text-text-tertiary">{error?.message || 'Enterprise guide is not available yet'}</p>
        <Link
          href={`/${workspaceSlug}/analysis/jobs/${jobId}`}
          className="mt-4 px-4 py-2 rounded-md border border-border bg-card text-[13px] text-foreground hover:bg-white/5 transition-colors"
        >
          Back to Job
        </Link>
      </div>
    );
  }

  const criticalCount = guide.critical_issues?.length ?? 0;
  const highCount = guide.high_issues?.length ?? 0;
  const mediumCount = guide.medium_issues?.length ?? 0;
  const hasIssues = criticalCount > 0 || highCount > 0 || mediumCount > 0;

  const topIssue = (() => {
    const all = [
      ...(guide.critical_issues as Record<string, string>[] | undefined)?.map(i => ({ ...i, severity: 'critical' })) ?? [],
      ...(guide.high_issues as Record<string, string>[] | undefined)?.map(i => ({ ...i, severity: 'high' })) ?? [],
      ...(guide.medium_issues as Record<string, string>[] | undefined)?.map(i => ({ ...i, severity: 'medium' })) ?? [],
    ];
    return all[0] ?? null;
  })();

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Link
            href={`/${workspaceSlug}/analysis/jobs/${jobId}`}
            className="p-1.5 border border-border bg-card rounded-md text-text-tertiary hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground flex items-center gap-2">
            <FileText className="w-5 h-5 text-venom-yellow" />
            Enterprise Guide
          </h1>
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border bg-card text-[12px] text-text-secondary hover:text-foreground hover:border-venom-yellow/30 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
            {regenerating ? 'Refreshing...' : 'Regenerate'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto w-full p-6 space-y-5">
          <AiExecutiveSummarySection
            summary={guide.ai_executive_summary}
            jobId={jobId}
          />

          <PriorityRecommendationSection
            issue={topIssue}
          />

          {guide.executive_summary && (
            <div className="bg-card border border-border rounded-lg">
              <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
                <FileText className="w-4 h-4 text-text-tertiary" />
                <h2 className="text-[13px] font-semibold text-foreground">Executive Summary</h2>
              </div>
              <div className="px-5 py-4">
                <p className="text-[13px] text-text-secondary leading-relaxed">{guide.executive_summary}</p>
              </div>
            </div>
          )}

          {hasIssues && (
            <div>
              <h2 className="text-[13px] font-semibold text-foreground mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4 text-text-tertiary" />
                Issues
              </h2>
              <div className="space-y-2">
                {criticalCount > 0 && (
                  <AccordionSection title="Critical" count={criticalCount} severity="critical" defaultOpen>
                    {(guide.critical_issues as unknown[]).map((issue: unknown, i: number) => (
                      <IssueCard key={i} issue={issue as Record<string, string>} severity="critical" />
                    ))}
                  </AccordionSection>
                )}
                {highCount > 0 && (
                  <AccordionSection title="High" count={highCount} severity="high">
                    {(guide.high_issues as unknown[]).map((issue: unknown, i: number) => (
                      <IssueCard key={i} issue={issue as Record<string, string>} severity="high" />
                    ))}
                  </AccordionSection>
                )}
                {mediumCount > 0 && (
                  <AccordionSection title="Medium" count={mediumCount} severity="medium">
                    {(guide.medium_issues as unknown[]).map((issue: unknown, i: number) => (
                      <IssueCard key={i} issue={issue as Record<string, string>} severity="medium" />
                    ))}
                  </AccordionSection>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {guide.architecture_review && (
              <div className="bg-card border border-border rounded-lg">
                <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
                  <Layers className="w-4 h-4 text-text-tertiary" />
                  <h2 className="text-[13px] font-semibold text-foreground">Architecture Review</h2>
                </div>
                <div className="px-5 py-4 space-y-1.5 text-[13px] text-text-secondary leading-relaxed">
                  {Object.entries(guide.architecture_review).map(([key, value]) => (
                    <p key={key}>
                      <span className="text-foreground font-medium">{key.replace(/_/g, ' ')}: </span>
                      {String(value)}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {guide.capacity_analysis && (
              <div className="bg-card border border-border rounded-lg">
                <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
                  <Gauge className="w-4 h-4 text-text-tertiary" />
                  <h2 className="text-[13px] font-semibold text-foreground">Capacity Analysis</h2>
                </div>
                <div className="px-5 py-4 space-y-3">
                  {Object.entries(guide.capacity_analysis).map(([key, value]) => {
                    const IconCmp = key.includes('rpm') ? Zap : key.includes('break') ? Users : key.includes('bottleneck') ? AlertCircle : null;
                    return (
                      <div key={key} className="flex items-center gap-2.5">
                        {IconCmp && <IconCmp className="w-4 h-4 text-text-tertiary shrink-0" />}
                        <div className={cn(!IconCmp && 'col-span-2')}>
                          <p className="text-[11px] text-text-tertiary uppercase tracking-wider">{key.replace(/_/g, ' ')}</p>
                          <p className="text-[13px] text-foreground font-mono">{String(value)}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {guide.migration_path && guide.migration_path.length > 0 && (
            <div>
              <h2 className="text-[13px] font-semibold text-foreground mb-3 flex items-center gap-2">
                <Route className="w-4 h-4 text-text-tertiary" />
                Migration Path
              </h2>
              <div className="space-y-2">
                {(guide.migration_path as unknown[]).map((step: unknown, i: number) => {
                  const item = step as Record<string, unknown>;
                  return (
                    <div key={i} className="border border-border rounded-lg bg-card p-4 hover:border-venom-yellow/30 transition-colors">
                      <div className="flex items-center gap-2.5 mb-2">
                        <span className="w-6 h-6 rounded-full bg-venom-yellow/20 text-venom-yellow text-[11px] font-bold flex items-center justify-center shrink-0">
                          {i + 1}
                        </span>
                        <p className="text-[13px] font-medium text-foreground">{item.title as string}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {item.score_impact != null && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 font-medium">+{item.score_impact as number} score</span>
                        )}
                        {item.rpm_gain != null && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 font-medium">+{item.rpm_gain as number} RPM</span>
                        )}
                        {item.effort != null && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-krait-surface3 text-text-secondary">{item.effort as string}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
