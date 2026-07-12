'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Zap, AlertCircle, Gauge, Users, Clock, Activity,
  Loader2,
} from 'lucide-react';
import { usePerfMetrics, useSimulationResults } from '@/lib/hooks/use-analysis';
import { Badge } from '@/components/ui/shadcn';
import { SimulationStatus } from '@/types/domain/analysis';
import { cn } from '@/lib/utils';
import type { PerformanceMetric, SimulationResult } from '@/types/domain/analysis';
import { ChartCard } from '@/components/analysis/chart-card';

const SIM_STATUS: Record<SimulationStatus, { label: string; class: string }> = {
  [SimulationStatus.STABLE]: { label: 'Stable', class: 'bg-green-500/20 text-green-400 border-green-500/30' },
  [SimulationStatus.DEGRADED]: { label: 'Degraded', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  [SimulationStatus.FAILING]: { label: 'Failing', class: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

const BOTTLENECK_COLORS: Record<string, string> = {
  n_plus_one: '#ef4444',
  sync_external_call: '#f97316',
  unbounded_query: '#eab308',
  sync_in_async: '#a855f7',
  high_complexity: '#ec4899',
  file_io_in_request: '#06b6d4',
  no_caching: '#6366f1',
  serialization_bottleneck: '#84cc16',
  many_db_queries: '#f43f5e',
  memory_pressure: '#d946ef',
  loop_complexity: '#14b8a6',
};

const SEVERITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#f97316',
  low: '#eab308',
};

function MetricCardSm({
  icon: Icon,
  value,
  label,
  color,
}: {
  icon: typeof Zap;
  value: string | number;
  label: string;
  color: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-4 flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}15` }}
      >
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
      <div>
        <p className="text-xl font-bold text-foreground tabular-nums leading-none">{value}</p>
        <p className="text-[11px] text-text-tertiary mt-1">{label}</p>
      </div>
    </div>
  );
}

function LatencyBarChart({ metrics }: { metrics: PerformanceMetric[] }) {
  const [expanded, setExpanded] = useState(false);
  const sliced = expanded ? metrics : metrics.slice(0, 8);

  if (metrics.length === 0) return null;

  const maxLatency = Math.max(...metrics.map(m => m.p99_latency_ms ?? 0), 1);

  return (
    <ChartCard title="Latency Distribution (p50 / p95 / p99)" icon={Clock}>
      <div className="space-y-1">
        {sliced.map((m) => {
          const p50 = m.p50_latency_ms ?? 0;
          const p95 = m.p95_latency_ms ?? 0;
          const p99 = m.p99_latency_ms ?? 0;
          return (
            <div key={m.id} className="grid grid-cols-[80px_1fr_60px] gap-2 items-center text-[11px]">
              <span className="text-muted-foreground truncate font-mono">{m.http_method || ''} {m.endpoint?.split('/').pop() || ''}</span>
              <div className="flex items-center gap-0.5 h-5">
                <div
                  className="h-3 rounded-l-sm bg-green-500/60"
                  style={{ width: `${(p50 / maxLatency) * 100}%`, minWidth: p50 > 0 ? 4 : 0 }}
                  title={`p50: ${p50}ms`}
                />
                <div
                  className="h-3 bg-yellow-500/60"
                  style={{ width: `${((p95 - p50) / maxLatency) * 100}%`, minWidth: p95 > p50 ? 4 : 0 }}
                  title={`p95: ${p95}ms`}
                />
                <div
                  className="h-3 rounded-r-sm bg-red-500/60"
                  style={{ width: `${((p99 - p95) / maxLatency) * 100}%`, minWidth: p99 > p95 ? 4 : 0 }}
                  title={`p99: ${p99}ms`}
                />
              </div>
              <span className="text-muted-foreground font-mono text-right">{p99}ms</span>
            </div>
          );
        })}
      </div>
      {metrics.length > 8 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-[11px] text-venom-yellow hover:underline"
        >
          {expanded ? 'Show less' : `Show all ${metrics.length} endpoints`}
        </button>
      )}
      <div className="flex gap-4 mt-3 text-[10px] text-text-tertiary">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-green-500/60" /> p50</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-yellow-500/60" /> p95</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-500/60" /> p99</span>
      </div>
    </ChartCard>
  );
}

function BottleneckDonut({ metrics }: { metrics: PerformanceMetric[] }) {
  const breakdown = useMemo(() => {
    const map: Record<string, number> = {};
    for (const m of metrics) {
      if (m.bottleneck_type) {
        for (const bt of m.bottleneck_type.split(',')) {
          const key = bt.trim();
          if (key) map[key] = (map[key] ?? 0) + 1;
        }
      }
    }
    return Object.entries(map)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [metrics]);

  if (breakdown.length === 0) return null;

  const total = breakdown.reduce((s, [, c]) => s + c, 0);
  const sorted = breakdown.sort((a, b) => b[1] - a[1]);

  return (
    <ChartCard title="Bottleneck Distribution" icon={Activity}>
      <div className="space-y-2.5">
        {sorted.map(([type, count]) => {
          const pct = (count / total) * 100;
          const color = BOTTLENECK_COLORS[type] ?? '#6366f1';
          return (
            <div key={type}>
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-foreground font-medium capitalize">{type.replace(/_/g, ' ')}</span>
                <span className="text-muted-foreground font-mono">{count}x</span>
              </div>
              <div className="h-2 bg-card border border-border rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, backgroundColor: color, boxShadow: `0 0 6px ${color}40` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </ChartCard>
  );
}

function RpmBarChart({ metrics }: { metrics: PerformanceMetric[] }) {
  const [expanded, setExpanded] = useState(false);
  const sliced = expanded ? metrics : metrics.slice(0, 8);

  if (metrics.length === 0) return null;

  const maxRpm = Math.max(...metrics.map(m => m.estimated_rpm ?? 0), 1);

  return (
    <ChartCard title="Estimated RPM by Endpoint" icon={Gauge}>
      <div className="space-y-1.5">
        {sliced.map((m) => {
          const rpm = m.estimated_rpm ?? 0;
          const pct = (rpm / maxRpm) * 100;
          const severity = m.bottleneck_severity ?? 'low';
          const color = SEVERITY_COLORS[severity] ?? '#6366f1';
          return (
            <div key={m.id} className="grid grid-cols-[80px_1fr_50px] gap-2 items-center text-[11px]">
              <span className="text-muted-foreground truncate font-mono">{m.http_method || ''} {m.endpoint?.split('/').pop() || ''}</span>
              <div className="h-4 bg-card border border-border rounded-sm overflow-hidden">
                <div
                  className="h-full rounded-sm transition-all duration-500"
                  style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.7 }}
                />
              </div>
              <span className="text-foreground font-mono text-right tabular-nums">{rpm}</span>
            </div>
          );
        })}
      </div>
      {metrics.length > 8 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-[11px] text-venom-yellow hover:underline"
        >
          {expanded ? 'Show less' : `Show all ${metrics.length} endpoints`}
        </button>
      )}
    </ChartCard>
  );
}

function SimulationFlowChart({ simulations }: { simulations: SimulationResult[] }) {
  if (simulations.length === 0) return null;

  const points = simulations.map((s, i) => ({
    users: s.concurrent_users,
    errorRate: s.error_rate_pct ?? 0,
    rpm: s.overall_rpm ?? 0,
    status: s.status,
    isBreak: i > 0 && s.status === SimulationStatus.FAILING && simulations[i - 1].status !== SimulationStatus.FAILING,
  }));

  const width = 400;
  const height = 160;
  const padding = { top: 16, right: 16, bottom: 24, left: 40 };

  const maxUsers = Math.max(...points.map(p => p.users), 1);
  const maxError = Math.max(...points.map(p => p.errorRate), 100);

  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const toX = (u: number) => padding.left + (u / maxUsers) * plotW;
  const toY = (e: number) => padding.top + plotH - (e / maxError) * plotH;

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${toX(p.users).toFixed(1)},${toY(p.errorRate).toFixed(1)}`).join('');

  return (
    <ChartCard title="Simulation: Error Rate vs Concurrent Users" icon={Users}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        <defs>
          <linearGradient id="simArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {/* Grid */}
        {[0, 25, 50, 75, 100].map(y => (
          <g key={y}>
            <line x1={padding.left} y1={toY(y)} x2={width - padding.right} y2={toY(y)} stroke="hsl(var(--krait-border))" strokeWidth="0.5" strokeDasharray="3 3" opacity="0.4" />
            <text x={padding.left - 4} y={toY(y) + 3} textAnchor="end" fill="hsl(var(--text-tertiary))" fontSize="8" fontFamily="monospace">{y}%</text>
          </g>
        ))}

        {/* Area */}
        <path d={`${linePath}L${toX(points[points.length - 1].users).toFixed(1)},${toY(0).toFixed(1)}L${toX(points[0].users).toFixed(1)},${toY(0).toFixed(1)}Z`} fill="url(#simArea)" />

        {/* Line */}
        <path d={linePath} fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        {/* Points */}
        {points.map((p, i) => {
          const color = p.status === SimulationStatus.FAILING ? '#ef4444' : p.status === SimulationStatus.DEGRADED ? '#eab308' : '#22c55e';
          return (
            <g key={i}>
              <circle cx={toX(p.users)} cy={toY(p.errorRate)} r={4} fill={color} stroke="hsl(var(--card))" strokeWidth="2" />
              <title>{`${p.users.toLocaleString()} users\nError: ${p.errorRate}%\nRPM: ${p.rpm}\nStatus: ${p.status}`}</title>
            </g>
          );
        })}

        {/* X-axis label */}
        <text x={width / 2} y={height - 2} textAnchor="middle" fill="hsl(var(--text-tertiary))" fontSize="8" fontFamily="monospace">Concurrent Users</text>
      </svg>
      <div className="flex gap-4 mt-1 text-[10px] text-text-tertiary">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> Stable</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Degraded</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Failing</span>
      </div>
    </ChartCard>
  );
}

export default function PerformancePage() {
  const params = useParams<{ workspace: string; jobId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';

  const { data: perfData, isLoading: perfLoading, error: perfError } = usePerfMetrics(jobId);
  const { data: simData, isLoading: simLoading } = useSimulationResults(jobId);

  const metrics = (perfData?.metrics ?? []) as PerformanceMetric[];
  const simulations = (simData?.results ?? []) as SimulationResult[];

  const avgLatency = useMemo(() => {
    if (metrics.length === 0) return 0;
    return Math.round(metrics.reduce((s, m) => s + (m.p50_latency_ms ?? 0), 0) / metrics.length);
  }, [metrics]);

  const bottleneckCount = useMemo(() => {
    const set = new Set<string>();
    for (const m of metrics) {
      if (m.bottleneck_type) {
        for (const bt of m.bottleneck_type.split(',')) {
          const key = bt.trim();
          if (key) set.add(key);
        }
      }
    }
    return set.size;
  }, [metrics]);

  const breakpoint = useMemo(() => {
    const failing = simulations.find(s => s.status === SimulationStatus.FAILING);
    if (failing) return failing.concurrent_users.toLocaleString();
    if (simulations.length > 0) return `${simulations[simulations.length - 1].concurrent_users.toLocaleString()}+`;
    return '—';
  }, [simulations]);

  const totalRpm = useMemo(() => {
    if (metrics.length === 0) return 0;
    return Math.min(...metrics.map(m => m.estimated_rpm ?? 0));
  }, [metrics]);

  if (perfLoading || simLoading) {
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
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-venom-yellow animate-spin" />
        </div>
      </div>
    );
  }

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
        {/* Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCardSm icon={Gauge} value={totalRpm.toLocaleString()} label="Min Est. RPM" color="#3b82f6" />
          <MetricCardSm icon={Clock} value={`${avgLatency}ms`} label="Avg p50 Latency" color="#22c55e" />
          <MetricCardSm icon={Activity} value={bottleneckCount} label="Bottleneck Types" color="#f97316" />
          <MetricCardSm icon={Users} value={breakpoint} label="Breakpoint" color="#ef4444" />
        </div>

        {/* Performance Error */}
        {perfError && (
          <div className="flex items-center gap-2 text-color-error text-[13px] p-3 border border-red-500/30 bg-red-500/10 rounded-md">
            <AlertCircle className="w-4 h-4" />
            {perfError.message}
          </div>
        )}

        {/* Empty State */}
        {metrics.length === 0 && !perfError && (
          <div className="flex flex-col items-center justify-center py-16 text-center border border-border rounded-lg bg-card">
            <Gauge className="w-10 h-10 text-text-tertiary mb-3" />
            <p className="text-sm text-text-secondary font-medium">No performance metrics</p>
            <p className="text-xs text-text-tertiary mt-1">Endpoints were not detected during parsing.</p>
          </div>
        )}

        {metrics.length > 0 && (
          <>
            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LatencyBarChart metrics={metrics} />
              <BottleneckDonut metrics={metrics} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RpmBarChart metrics={metrics} />
              {simulations.length > 0 && <SimulationFlowChart simulations={simulations} />}
            </div>

            {/* Endpoint Table */}
            <ChartCard title="Endpoint Metrics" icon={Zap}>
              <div className="border border-border rounded-lg overflow-hidden">
                <div className="grid grid-cols-[70px_1.5fr_90px_70px_70px_70px_1.2fr] gap-2 p-3 border-b border-border bg-background/50 text-[11px] font-medium text-muted-foreground">
                  <div>Method</div>
                  <div>Endpoint</div>
                  <div>Est. RPM</div>
                  <div>p50</div>
                  <div>p95</div>
                  <div>p99</div>
                  <div>Bottleneck</div>
                </div>
                {metrics.map((m: PerformanceMetric) => {
                  const severity = m.bottleneck_severity ?? 'low';
                  const sevColor = SEVERITY_COLORS[severity] ?? '#6366f1';
                  return (
                    <div
                      key={m.id}
                      className={cn(
                        'grid grid-cols-[70px_1.5fr_90px_70px_70px_70px_1.2fr] gap-2 p-3 text-[12px] border-b border-border last:border-0 items-center',
                        m.bottleneck_type ? 'bg-yellow-500/5' : ''
                      )}
                    >
                      <Badge className="bg-card border border-border text-[10px] font-mono w-fit">{m.http_method || '—'}</Badge>
                      <span className="text-foreground truncate font-mono text-[11px]">{m.endpoint || '—'}</span>
                      <span className="text-foreground font-mono tabular-nums">{m.estimated_rpm ?? '—'}</span>
                      <span className="text-muted-foreground font-mono tabular-nums">{m.p50_latency_ms != null ? `${m.p50_latency_ms}ms` : '—'}</span>
                      <span className="text-muted-foreground font-mono tabular-nums">{m.p95_latency_ms != null ? `${m.p95_latency_ms}ms` : '—'}</span>
                      <span className="text-muted-foreground font-mono tabular-nums">{m.p99_latency_ms != null ? `${m.p99_latency_ms}ms` : '—'}</span>
                      <span className="flex items-center gap-1.5 text-[11px]">
                        {m.bottleneck_type ? (
                          <>
                            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: sevColor }} />
                            <span className="text-orange-400 truncate">{m.bottleneck_type.replace(/_/g, ' ')}</span>
                          </>
                        ) : (
                          <span className="text-green-400">—</span>
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
              {metrics.some(m => m.bottleneck_detail) && (
                <details className="mt-3">
                  <summary className="text-[11px] text-venom-yellow cursor-pointer hover:underline">Show bottleneck details</summary>
                  <div className="mt-2 space-y-1 text-[11px] text-text-tertiary">
                    {metrics.filter(m => m.bottleneck_detail).map(m => (
                      <p key={m.id} className="font-mono"><span className="text-foreground">{m.endpoint}:</span> {m.bottleneck_detail}</p>
                    ))}
                  </div>
                </details>
              )}
            </ChartCard>
          </>
        )}

        {/* Simulation Table */}
        {simulations.length > 0 && (
          <ChartCard title="Load Simulation Results" icon={Users}>
            <div className="border border-border rounded-lg overflow-hidden">
              <div className="grid grid-cols-[1fr_1fr_1fr_1fr] gap-3 p-3 border-b border-border bg-background/50 text-[12px] font-medium text-muted-foreground">
                <div>Concurrent Users</div>
                <div>Status</div>
                <div>RPM</div>
                <div>Error Rate</div>
              </div>
              {simulations.map((s: SimulationResult) => {
                const st = SIM_STATUS[s.status] ?? { label: s.status, class: '' };
                const isBreak = s.status === SimulationStatus.FAILING;
                return (
                  <div
                    key={s.id}
                    className={cn(
                      'grid grid-cols-[1fr_1fr_1fr_1fr] gap-3 p-3 text-[13px] border-b border-border last:border-0 items-center',
                      isBreak ? 'bg-red-500/5' : ''
                    )}
                  >
                    <span className="text-foreground font-mono font-medium">{s.concurrent_users.toLocaleString()}</span>
                    <Badge className={cn('border text-[11px] font-medium w-fit', st.class)}>{st.label}</Badge>
                    <span className="text-foreground font-mono">{s.overall_rpm?.toLocaleString() ?? '—'}</span>
                    <span className="text-muted-foreground font-mono">{s.error_rate_pct != null ? `${s.error_rate_pct}%` : '—'}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-2 text-[10px] text-text-tertiary">
              Simulation estimates system behavior under increasing concurrent user load based on static analysis heuristics.
            </p>
          </ChartCard>
        )}
      </div>
    </div>
  );
}