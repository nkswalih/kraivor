
'use client';

import { Database, Zap } from 'lucide-react';
import type { QueryStats } from '@/lib/api/knowledge-ai-api';

export function CacheStatsCard({ stats }: { stats: QueryStats | undefined }) {
  if (!stats) return null;

  const hitRate = stats.cache_hit_rate * 100;
  const color = hitRate > 70 ? 'text-green-400' : hitRate > 40 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Database className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium">Cache Performance</h3>
      </div>
      <div className="flex items-end gap-3 mb-3">
        <div className={`text-3xl font-bold ${color}`}>{hitRate.toFixed(0)}%</div>
        <div className="text-[11px] text-muted-foreground mb-1">hit rate</div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-accent/50 rounded p-2">
          <div className="text-[13px] font-medium text-foreground">{stats.cache_hits}</div>
          <div className="text-[10px] text-muted-foreground">Cache Hits</div>
        </div>
        <div className="bg-accent/50 rounded p-2">
          <div className="text-[13px] font-medium text-foreground">{stats.total_sources_fetched}</div>
          <div className="text-[10px] text-muted-foreground">Sources Fetched</div>
        </div>
      </div>
    </div>
  );
}
