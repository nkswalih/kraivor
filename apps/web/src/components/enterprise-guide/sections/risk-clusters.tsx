'use client';

import { cn } from '@/lib/utils';
import type { BusinessRisk, TechnicalDebt, IssueCluster, Hotspot, ScalabilityReview } from '@/types/domain/analysis';
import { SectionCard, SectionHeader, SectionBody, RiskBadge, HealthBar, SeverityLabel, GradeBadge } from './common';
import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, Building, Shield, Clock, Server, Database } from 'lucide-react';

export function BusinessRiskSection({
  data,
}: {
  data: BusinessRisk | null | undefined;
}) {
  if (!data) return null;

  const risks = [
    { key: 'revenue_risk', label: 'Revenue Risk', value: data.revenue_risk, icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { key: 'customer_impact', label: 'Customer Impact', value: data.customer_impact, icon: <Building className="w-3.5 h-3.5" /> },
    { key: 'compliance_risk', label: 'Compliance Risk', value: data.compliance_risk, icon: <Shield className="w-3.5 h-3.5" /> },
    { key: 'reputation_risk', label: 'Reputation Risk', value: data.reputation_risk, icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { key: 'downtime_risk', label: 'Downtime Risk', value: data.downtime_risk, icon: <Clock className="w-3.5 h-3.5" /> },
    { key: 'operational_risk', label: 'Operational Risk', value: data.operational_risk, icon: <Server className="w-3.5 h-3.5" /> },
  ];

  return (
    <SectionCard>
      <SectionHeader title="Business Risk Assessment" />
      <SectionBody>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {risks.map((risk) => (
            <div
              key={risk.key}
              className={cn(
                'rounded-lg p-3 border text-center',
                risk.value === 'critical' ? 'bg-red-500/10 border-red-500/30' :
                risk.value === 'high' ? 'bg-venom-orange/10 border-venom-orange/30' :
                risk.value === 'medium' ? 'bg-venom-amber/10 border-venom-amber/30' :
                'bg-krait-surface1/50 border-border/50'
              )}
            >
              <div className="flex justify-center mb-1 text-foreground">{risk.icon}</div>
              <p className="text-[10px] text-text-tertiary uppercase tracking-wider">{risk.label}</p>
              <RiskBadge level={risk.value} />
            </div>
          ))}
        </div>
        {data.details && (
          <p className="text-[11px] text-text-tertiary mt-3 leading-relaxed border-t border-border pt-3">
            {data.details}
          </p>
        )}
      </SectionBody>
    </SectionCard>
  );
}

export function TechnicalDebtSection({
  data,
}: {
  data: TechnicalDebt | null | undefined;
}) {
  if (!data) return null;

  const debts = Object.entries(data).map(([key, val]) => ({
    key,
    label: val.label ?? key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()),
    count: val.count,
    hours: val.estimated_hours,
    severity: val.severity,
  }));

  const totalHours = debts.reduce((s, d) => s + d.hours, 0);

  return (
    <SectionCard>
      <SectionHeader title="Technical Debt" />
      <SectionBody>
        <div className="space-y-2">
          {debts.filter(d => d.count > 0).map((debt) => (
            <div
              key={debt.key}
              className={cn(
                'rounded-lg p-3 border',
                debt.severity === 'critical' ? 'border-red-500/20 bg-red-500/5' :
                debt.severity === 'high' ? 'border-venom-orange/20 bg-venom-orange/5' :
                'border-border/50 bg-krait-surface1/30'
              )}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <SeverityLabel severity={debt.severity} />
                  <span className="text-[12px] font-medium text-foreground">{debt.label}</span>
                </div>
                <span className="text-[11px] text-text-secondary">{debt.hours}h</span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-text-tertiary">
                <span>{debt.count} findings</span>
                <span>·</span>
                <span>{Math.round(debt.hours / Math.max(1, debt.count) * 60)}m avg</span>
              </div>
              <div className="mt-1.5">
                <div className="h-1.5 rounded-full bg-krait-surface2 overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full',
                      debt.severity === 'critical' ? 'bg-red-400' :
                      debt.severity === 'high' ? 'bg-venom-orange' :
                      'bg-venom-amber'
                    )}
                    style={{ width: `${totalHours > 0 ? (debt.hours / totalHours) * 100 : 0}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

export function IssueClusterSection({
  clusters,
}: {
  clusters: IssueCluster[] | null | undefined;
}) {
  if (!clusters || clusters.length === 0) return null;

  const primaryClusters = clusters.filter(c => c.severity === 'critical' || c.severity === 'high');
  const otherClusters = clusters.filter(c => c.severity !== 'critical' && c.severity !== 'high');

  return (
    <SectionCard>
      <SectionHeader
        title="Issue Clusters"
        badge={
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-krait-surface2 text-text-secondary">
            {clusters.length} groups
          </span>
        }
      />
      <SectionBody className="space-y-3">
        {primaryClusters.map((cluster) => (
          <ClusterCard key={cluster.cluster_id} cluster={cluster} expanded />
        ))}
        {otherClusters.map((cluster) => (
          <ClusterCard key={cluster.cluster_id} cluster={cluster} />
        ))}
      </SectionBody>
    </SectionCard>
  );
}

function ClusterCard({
  cluster,
  expanded: defaultExpanded = false,
}: {
  cluster: IssueCluster;
  expanded?: boolean;
}) {
  const [open, setOpen] = useState(defaultExpanded);

  return (
    <div
      className={cn(
        'rounded-lg border overflow-hidden',
        cluster.severity === 'critical' ? 'border-red-500/20' :
        cluster.severity === 'high' ? 'border-venom-orange/20' :
        'border-border'
      )}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-krait-surface1/30 transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          {open ? <ChevronDown className="w-3.5 h-3.5 shrink-0 text-text-tertiary" /> : <ChevronRight className="w-3.5 h-3.5 shrink-0 text-text-tertiary" />}
          <SeverityLabel severity={cluster.severity} />
          <span className="text-[12px] font-medium text-foreground truncate">{cluster.title}</span>
          <span className="text-[10px] text-text-tertiary shrink-0">({cluster.total_count})</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {cluster.cwe.length > 0 && (
            <span className="text-[9px] text-text-tertiary bg-krait-surface2 px-1.5 py-0.5 rounded">
              {cluster.cwe[0]}
            </span>
          )}
          {cluster.total_files > 1 && (
            <span className="text-[10px] text-text-tertiary">{cluster.total_files} files</span>
          )}
        </div>
      </button>
      {open && (
        <div className="px-4 py-3 border-t border-border bg-krait-surface1/20 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(cluster.severity_breakdown).map(([sev, count]) => (
              <span
                key={sev}
                className={cn(
                  'text-[10px] px-1.5 py-0.5 rounded',
                  sev === 'critical' ? 'bg-red-500/10 text-red-400' :
                  sev === 'high' ? 'bg-venom-orange/10 text-venom-orange' :
                  'bg-krait-surface2 text-text-tertiary'
                )}
              >
                {sev}: {count}
              </span>
            ))}
          </div>
          {cluster.affected_services.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {cluster.affected_services.map((svc) => (
                <span key={svc} className="text-[10px] px-1.5 py-0.5 rounded bg-krait-surface2 text-text-secondary">
                  {svc}
                </span>
              ))}
            </div>
          )}
          {cluster.root_cause && (
            <div>
              <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-0.5">Root Cause</p>
              <p className="text-[11px] text-text-secondary leading-relaxed">{cluster.root_cause}</p>
            </div>
          )}
          {cluster.enterprise_recommendation && (
            <div>
              <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-0.5">Recommendation</p>
              <p className="text-[11px] text-venom-yellow/80 leading-relaxed">{cluster.enterprise_recommendation}</p>
            </div>
          )}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              {cluster.cwe.map((c) => (
                <span key={c} className="text-[9px] px-1.5 py-0.5 rounded bg-krait-surface2 text-text-tertiary font-mono">{c}</span>
              ))}
              {cluster.owasp.map((o) => (
                <span key={o} className="text-[9px] px-1.5 py-0.5 rounded bg-krait-surface2 text-text-tertiary font-mono">{o}</span>
              ))}
            </div>
            {cluster.estimated_fix_time > 0 && (
              <span className="text-[10px] text-text-tertiary">
                Est. {Math.round(cluster.estimated_fix_time / 60)}h
              </span>
            )}
          </div>
          {cluster.representative_file && (
            <p className="text-[10px] text-text-tertiary font-mono truncate">
              File: {cluster.representative_file}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function HotspotsSection({
  hotspots,
}: {
  hotspots: Hotspot[] | null | undefined;
}) {
  if (!hotspots || hotspots.length === 0) return null;

  return (
    <SectionCard>
      <SectionHeader title="Hotspots" />
      <SectionBody>
        <div className="space-y-2">
          {hotspots.map((spot) => (
            <div
              key={spot.path}
              className="rounded-lg border border-border bg-krait-surface1/30 p-3"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <SeverityLabel severity={spot.priority} />
                    <span className="text-[12px] font-medium text-foreground truncate">{spot.path}</span>
                  </div>
                  <p className="text-[10px] text-text-tertiary">{spot.total_findings} findings · {spot.reason}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  <span className="text-[16px] font-bold text-venom-orange">{spot.risk_score}</span>
                </div>
              </div>
              <HealthBar score={spot.risk_score} />
              <div className="flex items-center justify-between mt-2">
                <div className="flex gap-1">
                  {Object.entries(spot.severity_breakdown).map(([sev, count]) => (
                    <span
                      key={sev}
                      className={cn(
                        'text-[9px] px-1 py-0.5 rounded',
                        sev === 'critical' ? 'bg-red-500/10 text-red-400' :
                        'bg-krait-surface2 text-text-tertiary'
                      )}
                    >
                      {sev}: {count}
                    </span>
                  ))}
                </div>
                <span className="text-[10px] text-text-tertiary">
                  {Math.round(spot.estimated_effort / 60)}h
                </span>
              </div>
              <p className="text-[10px] text-venom-yellow/70 mt-1 leading-relaxed">
                Top: {spot.top_issue}
              </p>
            </div>
          ))}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

export function ScalabilityReviewSection({
  data,
}: {
  data: ScalabilityReview | null | undefined;
}) {
  if (!data) return null;

  return (
    <SectionCard>
      <SectionHeader title="Scalability Review" />
      <SectionBody className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 rounded-lg bg-krait-surface1/50 border border-border/50">
            <Database className="w-4 h-4 mx-auto mb-1 text-text-tertiary" />
            <p className="text-[16px] font-bold text-foreground">
              {data.estimated_rpm ? `${(data.estimated_rpm / 1000).toFixed(1)}k` : 'N/A'}
            </p>
            <p className="text-[9px] text-text-tertiary">Est. RPM</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-krait-surface1/50 border border-border/50">
            <Server className="w-4 h-4 mx-auto mb-1 text-text-tertiary" />
            <p className="text-[16px] font-bold text-foreground">
              {data.estimated_concurrent_users?.toLocaleString() ?? 'N/A'}
            </p>
            <p className="text-[9px] text-text-tertiary">Concurrent Users</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-krait-surface1/50 border border-border/50">
            <span className="text-[16px] font-bold">
              {data.horizontal_scaling_readiness?.grade ?? 'N/A'}
            </span>
            <p className="text-[9px] text-text-tertiary">H-Scale</p>
          </div>
        </div>
        {data.expected_bottleneck && (
          <div className="rounded-lg bg-venom-amber/5 border border-venom-amber/20 p-3">
            <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-0.5">Expected Bottleneck</p>
            <p className="text-[11px] text-venom-amber leading-relaxed">{data.expected_bottleneck}</p>
          </div>
        )}
        {data.database_scalability && (
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-text-secondary">Database Scalability</span>
            <div className="flex items-center gap-2">
              <GradeBadge grade={data.database_scalability.grade} />
              <span className="text-text-tertiary">{data.database_scalability.recommendation?.slice(0, 60)}</span>
            </div>
          </div>
        )}
        {data.cache_recommendation && (
          <div className="text-[11px]">
            <span className="text-text-secondary font-medium">Cache: </span>
            <span className="text-text-tertiary">{data.cache_recommendation}</span>
          </div>
        )}
        {data.infrastructure_cost_projection && (
          <div className="text-[11px]">
            <span className="text-text-secondary font-medium">Cost: </span>
            <span className="text-text-tertiary">{data.infrastructure_cost_projection}</span>
          </div>
        )}
      </SectionBody>
    </SectionCard>
  );
}
