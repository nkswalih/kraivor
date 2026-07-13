'use client';

import { Globe, CheckCircle, XCircle } from 'lucide-react';
import type { QueryStats } from '@/lib/api/knowledge-ai-api';

export function SourceReliabilityCard({ stats }: { stats: QueryStats | undefined }) {
  // This is a placeholder — real data would come from source reliability endpoint
  // For now, show basic info from query stats
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Globe className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium">Source Overview</h3>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground">Total Sources Fetched</span>
          <span className="text-[13px] font-medium text-foreground">{stats?.total_sources_fetched ?? 0}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground">Period</span>
          <span className="text-[13px] font-medium text-foreground">{stats?.period_hours ?? 24}h</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground">Error Rate</span>
          <span className={`text-[13px] font-medium ${(stats?.error_rate ?? 0) < 0.05 ? 'text-green-400' : 'text-yellow-400'}`}>
            {((stats?.error_rate ?? 0) * 100).toFixed(1)}%
          </span>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-border">
        <p className="text-[11px] text-muted-foreground">
          For detailed per-provider reliability, use the API endpoint: <code className="text-venom-yellow">/v1/knowledge/monitoring/sources/{'{workspace_id}'}</code>
        </p>
      </div>
    </div>
  );
}
