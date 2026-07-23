'use client';

import { Clock, TrendingUp } from 'lucide-react';
import type { QueryStats } from '@/lib/api/knowledge-ai-api';

export function QueryLatencyCard({ stats }: { stats: QueryStats | undefined }) {
  if (!stats) return null;

  const p50Color = stats.p50_latency_ms < 200 ? 'text-green-400' : stats.p50_latency_ms < 500 ? 'text-yellow-400' : 'text-red-400';
  const p95Color = stats.p95_latency_ms < 500 ? 'text-green-400' : stats.p95_latency_ms < 1000 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium">Query Latency</h3>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className={`text-2xl font-bold ${p50Color}`}>{Math.round(stats.p50_latency_ms)}ms</div>
          <div className="text-[11px] text-muted-foreground">P50</div>
        </div>
        <div>
          <div className={`text-2xl font-bold ${p95Color}`}>{Math.round(stats.p95_latency_ms)}ms</div>
          <div className="text-[11px] text-muted-foreground">P95</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{Math.round(stats.avg_latency_ms)}ms</div>
          <div className="text-[11px] text-muted-foreground">Avg</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{Math.round(stats.max_latency_ms)}ms</div>
          <div className="text-[11px] text-muted-foreground">Max</div>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-border">
        <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <TrendingUp className="w-3 h-3" />
          {stats.total_queries} queries in last {stats.period_hours}h
        </div>
      </div>
    </div>
  );
}
