'use client';

import { AlertTriangle, CheckCircle } from 'lucide-react';
import type { QueryStats } from '@/lib/api/knowledge-ai-api';

export function ErrorRateCard({ stats }: { stats: QueryStats | undefined }) {
  if (!stats) return null;

  const errorRate = stats.error_rate * 100;
  const isHealthy = errorRate < 5;
  const color = isHealthy ? 'text-green-400' : errorRate < 15 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        {isHealthy ? (
          <CheckCircle className="w-4 h-4 text-green-400" />
        ) : (
          <AlertTriangle className="w-4 h-4 text-yellow-400" />
        )}
        <h3 className="text-[13px] font-medium">Error Rate</h3>
      </div>
      <div className="flex items-end gap-3">
        <div className={`text-3xl font-bold ${color}`}>{errorRate.toFixed(1)}%</div>
        <div className="text-[11px] text-muted-foreground mb-1">
          {stats.errors} errors / {stats.total_queries} queries
        </div>
      </div>
      <div className="mt-3">
        <div className="h-2 bg-border rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isHealthy ? 'bg-green-400' : errorRate < 15 ? 'bg-yellow-400' : 'bg-red-400'}`}
            style={{ width: `${Math.min(errorRate, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
