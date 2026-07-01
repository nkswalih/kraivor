'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, FileText, Loader2, AlertCircle, ChevronDown, ChevronRight, Users, Zap, RefreshCw } from 'lucide-react';
import { useEnterpriseGuide } from '@/lib/hooks/use-analysis';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';

function AccordionSection({
  title,
  count,
  children,
  defaultOpen = false,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-lg bg-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          {open ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
          <span className="text-[13px] font-medium text-foreground">{title}</span>
          <span className="text-[11px] text-text-tertiary bg-krait-surface2 px-2 py-0.5 rounded-full">{count}</span>
        </div>
      </button>
      {open && <div className="border-t border-border p-4">{children}</div>}
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
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 text-venom-yellow animate-spin" />
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

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center gap-3">
          <Link
            href={`/${workspaceSlug}/analysis/jobs/${jobId}`}
            className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" /> Enterprise Guide
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

      <div className="flex-1 overflow-y-auto p-6 max-w-3xl space-y-6">
        {/* Executive Summary */}
        {guide.executive_summary && (
          <div className="bg-card border border-border rounded-lg p-4">
            <h2 className="text-[13px] font-medium text-foreground uppercase tracking-wider mb-2">Executive Summary</h2>
            <p className="text-[13px] text-text-secondary leading-relaxed">{guide.executive_summary}</p>
          </div>
        )}

        {/* Issues by Severity */}
        {(criticalCount > 0 || highCount > 0 || mediumCount > 0) && (
          <div className="space-y-2">
            <h2 className="text-[13px] font-medium text-foreground uppercase tracking-wider mb-2">Issues</h2>
            {criticalCount > 0 && (
              <AccordionSection title="Critical" count={criticalCount} defaultOpen>
                <div className="space-y-2">
                  {(guide.critical_issues as unknown[]).map((issue: unknown, i: number) => {
                    const item = issue as Record<string, string>;
                    return (
                      <div key={i} className="border border-red-500/20 bg-red-500/5 rounded-md p-3">
                        <p className="text-[13px] font-medium text-red-400">{item.title}</p>
                        {item.file_path && <p className="text-[12px] text-text-tertiary font-mono mt-1">{item.file_path}</p>}
                        {item.description && <p className="text-[12px] text-text-tertiary mt-1">{item.description}</p>}
                        {item.recommendation && <p className="text-[12px] text-green-400 mt-2">{item.recommendation}</p>}
                      </div>
                    );
                  })}
                </div>
              </AccordionSection>
            )}
            {highCount > 0 && (
              <AccordionSection title="High" count={highCount}>
                <div className="space-y-2">
                  {(guide.high_issues as unknown[]).map((issue: unknown, i: number) => {
                    const item = issue as Record<string, string>;
                    return (
                      <div key={i} className="border border-orange-500/20 bg-orange-500/5 rounded-md p-3">
                        <p className="text-[13px] font-medium text-orange-400">{item.title as string}</p>
                        {item.file_path && <p className="text-[12px] text-text-tertiary font-mono mt-1">{item.file_path as string}</p>}
                        {item.recommendation && <p className="text-[12px] text-green-400 mt-2">{item.recommendation as string}</p>}
                      </div>
                    );
                  })}
                </div>
              </AccordionSection>
            )}
            {mediumCount > 0 && (
              <AccordionSection title="Medium" count={mediumCount}>
                <div className="space-y-2">
                  {(guide.medium_issues as unknown[]).map((issue: unknown, i: number) => {
                    const item = issue as Record<string, string>;
                    return (
                      <div key={i} className="border border-yellow-500/20 bg-yellow-500/5 rounded-md p-3">
                        <p className="text-[13px] font-medium text-yellow-400">{item.title as string}</p>
                        {item.recommendation && <p className="text-[12px] text-green-400 mt-2">{item.recommendation as string}</p>}
                      </div>
                    );
                  })}
                </div>
              </AccordionSection>
            )}
          </div>
        )}

        {/* Architecture Review */}
        {guide.architecture_review && (
          <div className="bg-card border border-border rounded-lg p-4">
            <h2 className="text-[13px] font-medium text-foreground uppercase tracking-wider mb-2">Architecture Review</h2>
            <div className="text-[13px] text-text-secondary leading-relaxed">
              {Object.entries(guide.architecture_review).map(([key, value]) => (
                <p key={key} className="mb-1">
                  <span className="text-text-primary font-medium">{key.replace(/_/g, ' ')}: </span>
                  {String(value)}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Capacity Analysis */}
        {guide.capacity_analysis && (
          <div className="bg-card border border-border rounded-lg p-4">
            <h2 className="text-[13px] font-medium text-foreground uppercase tracking-wider mb-2">Capacity Analysis</h2>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(guide.capacity_analysis).map(([key, value]) => (
                <div key={key} className="flex items-center gap-2">
                  {key.includes('rpm') && <Zap className="w-4 h-4 text-yellow-400" />}
                  {key.includes('break') && <Users className="w-4 h-4 text-blue-400" />}
                  {key.includes('bottleneck') && <AlertCircle className="w-4 h-4 text-orange-400" />}
                  <div>
                    <p className="text-[11px] text-text-tertiary uppercase">{key.replace(/_/g, ' ')}</p>
                    <p className="text-[13px] text-foreground font-mono">{String(value)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Migration Path */}
        {guide.migration_path && guide.migration_path.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-[13px] font-medium text-foreground uppercase tracking-wider mb-2">Migration Path</h2>
            <div className="space-y-2">
              {(guide.migration_path as unknown[]).map((step: unknown, i: number) => {
                const item = step as Record<string, unknown>;
                return (
                  <div key={i} className="border border-border rounded-lg bg-card p-4 hover:border-venom-yellow/30 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-6 h-6 rounded-full bg-venom-yellow/20 text-venom-yellow text-[11px] font-bold flex items-center justify-center">
                        {i + 1}
                      </span>
                      <p className="text-[13px] font-medium text-foreground">{item.title as string}</p>
                    </div>
                    {item.score_impact != null && (
                      <span className="text-[11px] text-green-400">+{item.score_impact as number} score</span>
                    )}
                    {item.rpm_gain != null && (
                      <span className="text-[11px] text-yellow-400 ml-2">+{item.rpm_gain as number} RPM</span>
                    )}
                    {item.effort != null && (
                      <span className="text-[11px] text-text-tertiary ml-2">{item.effort as string}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
