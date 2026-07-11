'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, FileText, RefreshCw, AlertCircle } from 'lucide-react';
import { useEnterpriseGuide } from '@/lib/hooks/use-analysis';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { EnterpriseGuideContent } from '@/components/enterprise-guide/enterprise-guide-content';

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
        <EnterpriseGuideContent guide={guide} />
      </div>
    </div>
  );
}
