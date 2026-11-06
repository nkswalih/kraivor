'use client';

import { cn } from '@/lib/utils';
import type { RepositoryHealth, ScorecardCategory } from '@/types/domain/analysis';
import { SectionCard, SectionHeader, SectionBody, ScoreBadge, GradeBadge, StatusDot, HealthBar, DimensionRow, RiskBadge } from './common';

export function ExecutiveSummaryHeader({
  data,
}: {
  data: RepositoryHealth | null | undefined;
}) {
  if (!data) return null;

  return (
    <SectionCard className="overflow-hidden">
      <div className="p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-[11px] text-text-tertiary uppercase tracking-wider mb-1">
              Repository Health
            </p>
            <h1 className="text-[22px] font-bold text-foreground">
              {data.repository_health === 'excellent' ? 'Healthy' :
               data.repository_health === 'good' ? 'Good' :
               data.repository_health === 'needs_work' ? 'Needs Work' :
               data.repository_health === 'needs_attention' ? 'Needs Attention' :
               data.repository_health}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <GradeBadge grade={data.overall_grade} />
            <ScoreBadge score={data.overall_score} size="lg" />
          </div>
        </div>

        <HealthBar score={data.overall_score} className="mb-5" />

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Production Readiness" value={data.production_readiness} />
          <MetricCard label="Deployment" value={data.deployment_readiness === 'ready' ? 'Ready' : data.deployment_readiness === 'conditional' ? 'Conditional' : 'Not Ready'} />
          <MetricCard label="Release" value={data.release_recommendation === 'go' ? 'Go' : data.release_recommendation === 'proceed_with_caution' ? 'Proceed w/ Caution' : 'No-Go'} />
          <MetricCard label="Business Risk" value={data.business_risk === 'critical' ? 'Critical' : data.business_risk === 'high' ? 'High' : data.business_risk === 'medium' ? 'Medium' : 'Low'} highlight={data.business_risk === 'critical' || data.business_risk === 'high'} />
        </div>

        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border">
          <Detail label="Eng. Risk" value={data.engineering_risk} />
          <Detail label="Tech Debt" value={data.technical_debt_level} />
          <Detail label="Est. Remediation" value={data.estimated_remediation_time} />
        </div>
      </div>
    </SectionCard>
  );
}

function MetricCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className={cn(
      'rounded-lg p-3 border',
      highlight ? 'bg-red-500/5 border-red-500/20' : 'bg-krait-surface1/50 border-border/50'
    )}>
      <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-1">{label}</p>
      <p className={cn('text-[13px] font-semibold capitalize', highlight ? 'text-red-400' : 'text-foreground')}>
        {value.replace(/_/g, ' ')}
      </p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-[10px] text-text-tertiary uppercase tracking-wider">{label}</p>
      <p className="text-[13px] font-semibold text-foreground capitalize mt-0.5">
        {value.replace(/_/g, ' ')}
      </p>
    </div>
  );
}

export function EngineeringScorecards({
  data,
}: {
  data: Record<string, ScorecardCategory> | null | undefined;
}) {
  if (!data || Object.keys(data).length === 0) return null;

  return (
    <SectionCard>
      <SectionHeader title="Engineering Scorecard" />
      <SectionBody>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Object.entries(data).map(([key, cat]) => (
            <ScorecardCard key={key} categoryKey={key} data={cat} />
          ))}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  security: 'Security',
  performance: 'Performance',
  reliability: 'Reliability',
  maintainability: 'Maintainability',
  devops: 'DevOps',
};

function ScorecardCard({
  categoryKey,
  data,
}: {
  categoryKey: string;
  data: ScorecardCategory;
}) {
  return (
    <div className="rounded-lg border border-border bg-krait-surface1/30 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[12px] font-semibold text-foreground">
          {CATEGORY_LABELS[categoryKey] ?? categoryKey}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-tertiary">{data.industry_comparison}</span>
          <GradeBadge grade={data.grade} />
        </div>
      </div>
      <ScoreBadge score={data.score} size="lg" />
      <HealthBar score={data.score} className="mt-2 mb-3" />
      {data.total_findings > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {Object.entries(data.severity_breakdown).map(([sev, count]) => (
            <span
              key={sev}
              className={cn(
                'text-[10px] px-1.5 py-0.5 rounded',
                sev === 'critical' ? 'bg-red-500/10 text-red-400' :
                sev === 'high' ? 'bg-venom-orange/10 text-venom-orange' :
                sev === 'medium' ? 'bg-venom-amber/10 text-venom-amber' :
                'bg-krait-surface2 text-text-tertiary'
              )}
            >
              {sev}:{count}
            </span>
          ))}
        </div>
      )}
      {data.biggest_problem && (
        <p className="text-[10px] text-text-tertiary mt-2 leading-relaxed">
          <span className="text-text-secondary font-medium">Issue: </span>
          {data.biggest_problem}
        </p>
      )}
      {data.best_recommendation && (
        <p className="text-[10px] text-venom-yellow/80 mt-1 leading-relaxed">
          <span className="font-medium">Fix: </span>
          {data.best_recommendation}
        </p>
      )}
    </div>
  );
}

export function RepositoryHealthCards({
  data,
}: {
  data: Record<string, ScorecardCategory> | null | undefined;
}) {
  if (!data) return null;
  const dims = [
    { key: 'stability', label: 'Stability', score: null },
    { key: 'security_maturity', label: 'Security Maturity', score: null },
    { key: 'performance_maturity', label: 'Performance Maturity', score: null },
    { key: 'architecture_quality', label: 'Architecture Quality', score: null },
    { key: 'maintainability', label: 'Maintainability', score: null },
    { key: 'devops_readiness', label: 'DevOps Readiness', score: null },
  ];

  return (
    <SectionCard>
      <SectionHeader title="Repository Health" />
      <SectionBody>
        <div className="divide-y divide-border/50">
          {dims.map((dim) => {
            const catData = data[dim.key] as ScorecardCategory | undefined;
            return (
              <DimensionRow
                key={dim.key}
                label={dim.label}
                score={catData?.score ?? null}
                grade={catData?.grade ?? null}
                status="needs_work"
              />
            );
          })}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

export function EstimatedEffortSummary({
  data,
}: {
  data: {
    total_minutes?: number;
    total_hours?: number;
    total_days?: number;
    by_category?: Record<string, number>;
    by_severity?: Record<string, number>;
  } | null | undefined;
}) {
  if (!data) return null;

  return (
    <SectionCard>
      <SectionHeader title="Estimated Remediation Effort" />
      <SectionBody className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 rounded-lg bg-krait-surface1/50 border border-border/50">
            <p className="text-[20px] font-bold text-foreground">{Math.round(data.total_hours ?? 0)}</p>
            <p className="text-[10px] text-text-tertiary">Hours</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-krait-surface1/50 border border-border/50">
            <p className="text-[20px] font-bold text-foreground">{Math.round(data.total_days ?? 0)}</p>
            <p className="text-[10px] text-text-tertiary">Days</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-krait-surface1/50 border border-border/50">
            <p className="text-[20px] font-bold text-foreground">{Math.round(data.total_minutes ?? 0)}</p>
            <p className="text-[10px] text-text-tertiary">Minutes</p>
          </div>
        </div>
        {data.by_category && Object.keys(data.by_category).length > 0 && (
          <div>
            <p className="text-[11px] font-semibold text-foreground mb-2">By Category</p>
            <div className="space-y-1.5">
              {Object.entries(data.by_category)
                .sort(([, a], [, b]) => b - a)
                .map(([cat, mins]) => (
                  <div key={cat} className="flex items-center justify-between text-[11px]">
                    <span className="text-text-secondary capitalize">{cat.replace(/_/g, ' ')}</span>
                    <span className="text-foreground font-medium">{Math.round(mins)}m</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </SectionBody>
    </SectionCard>
  );
}
