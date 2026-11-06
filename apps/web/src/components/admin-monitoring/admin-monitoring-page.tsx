'use client';

import { useQueryStats, useKnowledgeStats, useKnowledgeHealth } from '@/lib/hooks/use-knowledge-dashboard';
import { QueryLatencyCard } from './query-latency-card';
import { CacheStatsCard } from './cache-stats-card';
import { SourceReliabilityCard } from './source-reliability-card';
import { ErrorRateCard } from './error-rate-card';
import { TopQueriesCard } from './top-queries-card';
import { HealthOverviewCard } from './health-overview-card';
import { SkeletonCard } from '@/components/ui/skeletons';

export function AdminMonitoringPage({ workspaceId }: { workspaceId: string }) {
  const queryStats = useQueryStats(workspaceId);
  const stats = useKnowledgeStats(workspaceId);
  const health = useKnowledgeHealth(workspaceId);

  return (
    <div className="flex flex-col h-full animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div>
          <h1 className="text-lg font-medium">AI Monitoring</h1>
          <p className="text-[12px] text-muted-foreground">
            Developer monitoring panel — Knowledge engine performance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-muted-foreground">Auto-refresh: 30s</span>
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {queryStats.isLoading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            <>
              <QueryLatencyCard stats={queryStats.data} />
              <ErrorRateCard stats={queryStats.data} />
              <CacheStatsCard stats={queryStats.data} />
            </>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          {health.isLoading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            <>
              <HealthOverviewCard health={health.data} />
              <SourceReliabilityCard stats={queryStats.data} />
            </>
          )}
        </div>

        <div className="mt-4">
          {queryStats.isLoading ? <SkeletonCard /> : <TopQueriesCard stats={queryStats.data} />}
        </div>
      </div>
    </div>
  );
}
