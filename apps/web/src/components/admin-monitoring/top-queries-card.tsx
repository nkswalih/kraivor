'use client';

import { Search, Hash } from 'lucide-react';
import type { QueryStats } from '@/lib/api/knowledge-ai-api';

export function TopQueriesCard({ stats }: { stats: QueryStats | undefined }) {
  // Placeholder — real data would come from top-queries endpoint
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Search className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium">Query Summary</h3>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <div className="text-2xl font-bold text-foreground">{stats?.total_queries ?? 0}</div>
          <div className="text-[11px] text-muted-foreground">Total Queries</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-400">{stats?.cache_hits ?? 0}</div>
          <div className="text-[11px] text-muted-foreground">Cache Hits</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-400">{stats?.errors ?? 0}</div>
          <div className="text-[11px] text-muted-foreground">Errors</div>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-border">
        <p className="text-[11px] text-muted-foreground">
          For top queries, use: <code className="text-venom-yellow">/v1/knowledge/monitoring/top-queries/{'{workspace_id}'}</code>
        </p>
      </div>
    </div>
  );
}
