'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Zap, AlertCircle, Gauge, Users } from 'lucide-react';
import { usePerfMetrics, useSimulationResults } from '@/lib/hooks/use-analysis';
import { Badge, Skeleton } from '@/components/ui/shadcn';
import { SimulationStatus } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';
import type { PerformanceMetric, SimulationResult } from '@/types/domain/analysis';

const SIM_STATUS: Record<SimulationStatus, { label: string; class: string }> = {
  [SimulationStatus.STABLE]: { label: 'Stable', class: 'bg-green-500/20 text-green-400 border-green-500/30' },
  [SimulationStatus.DEGRADED]: { label: 'Degraded', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  [SimulationStatus.FAILING]: { label: 'Failing', class: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

export default function PerformancePage() {
  const params = useParams<{ workspace: string; jobId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';

  const { data: perfData, isLoading: perfLoading, error: perfError } = usePerfMetrics(jobId);
  const { data: simData, isLoading: simLoading } = useSimulationResults(jobId);

  const metrics = (perfData?.metrics ?? []) as PerformanceMetric[];
  const simulations = (simData?.results ?? []) as SimulationResult[];

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center gap-3 mb-2">
          <Link
            href={`/${workspaceSlug}/analysis/jobs/${jobId}`}
            className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" /> Performance
          </h1>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Performance Metrics */}
        <div>
          <h2 className="text-[13px] font-medium text-foreground uppercase tracking-wider mb-3">Endpoint Metrics</h2>
          {perfError ? (
            <div className="flex items-center gap-2 text-color-error text-[13px] p-3 border border-red-500/30 bg-red-500/10 rounded-md">
              <AlertCircle className="w-4 h-4" />
              {perfError.message}
            </div>
          ) : perfLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded-lg" />
              ))}
            </div>
          ) : metrics.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center border border-border rounded-lg bg-card">
              <Gauge className="w-8 h-8 text-text-tertiary mb-2" />
              <p className="text-sm text-text-secondary font-medium">No performance metrics</p>
            </div>
          ) : (
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="grid grid-cols-[80px_1.5fr_100px_100px_100px_1fr] gap-3 p-3 border-b border-border bg-background/50 text-[12px] font-medium text-muted-foreground">
                <div>Method</div>
                <div>Endpoint</div>
                <div>Est. RPM</div>
                <div>p50</div>
                <div>p95</div>
                <div>Bottleneck</div>
              </div>
              {metrics.map((m: PerformanceMetric) => (
                <div
                  key={m.id}
                  className={cn(
                    'grid grid-cols-[80px_1.5fr_100px_100px_100px_1fr] gap-3 p-3 text-[13px] border-b border-border last:border-0',
                    m.bottleneck_type ? 'bg-yellow-500/5' : ''
                  )}
                >
                  <Badge className="bg-card border border-border text-[11px] font-mono w-fit">
                    {m.http_method || '—'}
                  </Badge>
                  <span className="text-foreground truncate font-mono">{m.endpoint || '—'}</span>
                  <span className="text-foreground font-mono">{m.estimated_rpm ?? '—'}</span>
                  <span className="text-muted-foreground font-mono">{m.p50_latency_ms != null ? `${m.p50_latency_ms}ms` : '—'}</span>
                  <span className="text-muted-foreground font-mono">{m.p95_latency_ms != null ? `${m.p95_latency_ms}ms` : '—'}</span>
                  <span className="text-muted-foreground text-[12px]">
                    {m.bottleneck_type ? (
                      <span className="text-orange-400">{m.bottleneck_type.replace(/_/g, ' ')}</span>
                    ) : '—'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Load Simulation */}
        <div>
          <h2 className="text-[13px] font-medium text-foreground uppercase tracking-wider mb-3">Load Simulation</h2>
          {simLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded-lg" />
              ))}
            </div>
          ) : simulations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center border border-border rounded-lg bg-card">
              <Users className="w-8 h-8 text-text-tertiary mb-2" />
              <p className="text-sm text-text-secondary font-medium">No simulation results</p>
            </div>
          ) : (
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="grid grid-cols-[1fr_1fr_1fr_1fr] gap-3 p-3 border-b border-border bg-background/50 text-[12px] font-medium text-muted-foreground">
                <div>Concurrent Users</div>
                <div>Status</div>
                <div>RPM</div>
                <div>Error Rate</div>
              </div>
              {simulations.map((s: SimulationResult) => {
                const st = SIM_STATUS[s.status] ?? { label: s.status, class: '' };
                return (
                  <div
                    key={s.id}
                    className="grid grid-cols-[1fr_1fr_1fr_1fr] gap-3 p-3 text-[13px] border-b border-border last:border-0 items-center"
                  >
                    <span className="text-foreground font-mono font-medium">
                      {s.concurrent_users.toLocaleString()}
                    </span>
                    <Badge className={cn('border text-[11px] font-medium w-fit', st.class)}>
                      {st.label}
                    </Badge>
                    <span className="text-foreground font-mono">{s.overall_rpm?.toLocaleString() ?? '—'}</span>
                    <span className="text-muted-foreground font-mono">
                      {s.error_rate_pct != null ? `${s.error_rate_pct}%` : '—'}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
