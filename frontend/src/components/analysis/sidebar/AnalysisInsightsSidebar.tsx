'use client';

import { useState, useEffect } from 'react';
import { X, PanelRightClose } from 'lucide-react';
import { cn } from '@/lib/utils';
import { analysisInsightsBuilder } from '@/lib/analysis/insights-builder';
import type { AnalysisJob, Report, FindingsSummary, Finding } from '@/types/domain/analysis';
import { AIExecutiveSummaryCard } from './AIExecutiveSummaryCard';
import { PriorityRecommendationCard } from './PriorityRecommendationCard';
import { RepositoryOverviewCard } from './RepositoryOverviewCard';
import { EngineStatusCard } from './EngineStatusCard';
import { AnalysisMetadataCard } from './AnalysisMetadataCard';

interface AnalysisInsightsSidebarProps {
  job: AnalysisJob | null | undefined;
  report: Report | null | undefined;
  findingsSummary: FindingsSummary | null | undefined;
  findings: Finding[] | null | undefined;
  isLoading?: boolean;
  onViewFinding?: () => void;
  onClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function AnalysisInsightsSidebar({
  job,
  report,
  findingsSummary,
  findings,
  isLoading: externalLoading,
  onViewFinding,
  onClose,
  collapsed,
  onToggleCollapse,
}: AnalysisInsightsSidebarProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isLoading = externalLoading ?? !job;

  const insights = analysisInsightsBuilder(job, report, findingsSummary, findings);

  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        className="fixed right-4 top-24 z-40 p-2 rounded-lg bg-card border border-border text-text-tertiary hover:text-foreground transition-colors lg:hidden xl:flex"
        title="Show insights"
      >
        <PanelRightClose className="w-4 h-4" />
      </button>
    );
  }

  return (
    <aside
      className={cn(
        'w-full lg:w-[340px] xl:w-[360px] 2xl:w-[380px] shrink-0',
        'border-l border-border bg-background',
        'flex flex-col',
        'h-full overflow-y-auto',
      )}
    >
      {/* Mobile/tablet header with close */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border lg:hidden">
        <h2 className="text-[13px] font-semibold text-foreground">Analysis Insights</h2>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-text-tertiary hover:text-foreground transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Sticky inner scroll container for desktop */}
      <div
        className={cn(
          'flex-1 overflow-y-auto',
          'lg:sticky lg:top-0 lg:h-screen',
        )}
      >
        <div className="flex flex-col gap-4 p-4">
          <AIExecutiveSummaryCard
            data={insights.aiSummary}
            isLoading={isLoading}
          />

          <PriorityRecommendationCard
            data={insights.priorityRecommendation}
            isLoading={isLoading}
            onViewFinding={onViewFinding}
          />

          <RepositoryOverviewCard
            data={insights.repositoryOverview}
            isLoading={isLoading}
          />

          <EngineStatusCard
            items={insights.engineStatus}
            isLoading={isLoading}
          />

          <AnalysisMetadataCard
            data={insights.metadata}
            isLoading={isLoading}
          />

          {/* Collapse toggle for desktop */}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="hidden xl:flex items-center justify-center gap-1.5 py-2 rounded-lg border border-border bg-card text-[11px] text-text-tertiary hover:text-foreground hover:border-venom-yellow/30 transition-colors"
            >
              <PanelRightClose className="w-3.5 h-3.5" />
              Collapse sidebar
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
