'use client';

import { X, PanelRightClose } from 'lucide-react';
import { cn } from '@/lib/utils';
import { analysisInsightsBuilder, isJobInFlight } from '@/lib/analysis/insights-builder';
import {
  useAnalysisMetadata,
  useEnterpriseGuide,
  useEngines,
  useReEnrich,
} from '@/lib/hooks/use-analysis';
import type { AnalysisJob, Report, FindingsSummary, Finding } from '@/types/domain/analysis';
import { AIExecutiveSummaryCard } from './AIExecutiveSummaryCard';
import { PriorityRecommendationCard } from './PriorityRecommendationCard';
import { RepositoryOverviewCard } from './RepositoryOverviewCard';
import { EngineStatusCard } from './EngineStatusCard';
import { AnalysisMetadataCard } from './AnalysisMetadataCard';
import { ProjectContextCard } from './ProjectContextCard';

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
  const jobId = job?.job_id ?? null;
  // These requests outlive the page's own loading state, so the sidebar tracks
  // the one it needs rather than being told. The page used to pass
  // `isLoading || !job`, which was always false by the time it reached here --
  // the page returns a full-page spinner on loading and a not-found screen on a
  // missing job -- so every card's loading path was dead code.
  const { data: analysisMetadata } = useAnalysisMetadata(jobId);
  // The error was destructured away entirely, so a failed guide request left the
  // summary card claiming a summary was on its way. With `retry: false` on the
  // query that claim survived for the rest of the page's life -- and the run was
  // finished, so nothing would ever arrive to correct it.
  const {
    data: enterpriseGuide,
    isLoading: guideLoading,
    error: guideError,
    refetch: refetchGuide,
  } = useEnterpriseGuide(jobId);
  const { data: enginesResponse } = useEngines();

  const isLoading = externalLoading ?? !job;

  // Whether the run still has stages ahead of it. Computed once here because the
  // builder branches on it and so does the summary card, and the two must not
  // disagree about whether the job is finished.
  const running = !isLoading && isJobInFlight(job?.status);

  // A finished run whose guide request is still in flight is a third case, and
  // the one that produced the false footer: the summary had not been read yet,
  // rather than being absent or still being written. Both hooks settle without
  // retry, so `data === undefined` means "asked, not answered", not "no summary".
  //
  // `guideError` makes a fourth, and it is the only one we caused: the request
  // did not come back. Passing it through is the whole difference between "the
  // summary is coming" -- which for a finished run is a promise nothing will keep
  // -- and "we could not check".
  const guidePending = !isLoading && guideLoading;

  // Retrying the summary in place. The sidebar did not previously have any way to
  // ask for one, so a summary that failed to generate was a dead end from this
  // page: the only regenerate button lived on the enterprise guide page, a
  // different route, which a reader of a running analysis is not looking at.
  //
  // `onSuccess` is not wired to a toast here. The card's own state is the
  // feedback: the hook invalidates `analysis-guide`, the sidebar re-reads, and a
  // summary appears or the reason changes. A toast saying "regenerated" on a run
  // that then renders the same error is the failure this whole task is about.
  const reEnrich = useReEnrich();
  const retrySummary = () => {
    if (!jobId) return;
    reEnrich.mutate(jobId);
  };

  const aiExecutiveSummary = enterpriseGuide?.ai_executive_summary ?? null;
  const aiSummaryError = enterpriseGuide?.ai_summary_error ?? null;
  const insights = analysisInsightsBuilder(job, report, findingsSummary, findings, analysisMetadata, aiExecutiveSummary, enginesResponse?.engines, aiSummaryError);

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
          <ProjectContextCard
            job={job}
            metadata={analysisMetadata}
            isLoading={isLoading}
          />

          <AIExecutiveSummaryCard
            data={insights.aiSummary}
            isLoading={isLoading}
            isRunning={running}
            guidePending={guidePending}
            guideError={guideError}
            onRefetchGuide={() => void refetchGuide()}
            onRetry={retrySummary}
            isRetrying={reEnrich.isPending}
          />

          <PriorityRecommendationCard
            data={insights.priorityRecommendation}
            isLoading={isLoading}
            onViewFinding={onViewFinding}
          />

          {/* These two cards describe a finished run, and every figure in them
              comes from the report. While the job is still going, ProjectContext
              above carries everything actually measured -- and a repository
              overview with no languages beside an engine list with nothing scored
              reads as a broken panel rather than an unfinished one. The engine
              card stays: per-engine state is real from the moment each engine
              starts, which is the point of it. */}
          {!isJobInFlight(job?.status) && (
            <>
              <RepositoryOverviewCard
                data={insights.repositoryOverview}
                isLoading={isLoading}
              />

              <AnalysisMetadataCard
                data={insights.metadata}
                isLoading={isLoading}
              />
            </>
          )}

          <EngineStatusCard
            items={insights.engineStatus}
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
