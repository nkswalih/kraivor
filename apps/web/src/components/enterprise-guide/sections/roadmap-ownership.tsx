'use client';

import { cn } from '@/lib/utils';
import type { Sprint, OwnershipAssignment, AIRecommendation, QuickWin, ServiceHealth } from '@/types/domain/analysis';
import { SectionCard, SectionHeader, SectionBody, SeverityLabel, GradeBadge, StatusDot, HealthBar } from './common';
import { ArrowRight, Users, CheckCircle, Target, Clock } from 'lucide-react';

export function SprintRoadmapSection({
  data,
}: {
  data: Record<string, Sprint> | null | undefined;
}) {
  if (!data) return null;

  const sprints = Object.values(data).sort((a, b) => a.sprint_number - b.sprint_number);
  if (sprints.length === 0) return null;

  return (
    <SectionCard>
      <SectionHeader title="Sprint Roadmap" />
      <SectionBody>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {sprints.map((sprint) => (
            <div
              key={sprint.sprint_number}
              className="rounded-lg border border-border bg-krait-surface1/30 overflow-hidden"
            >
              <div className={cn(
                'px-3 py-2 border-b border-border',
                sprint.sprint_number === 1 ? 'bg-red-500/10' :
                sprint.sprint_number === 2 ? 'bg-venom-orange/10' :
                sprint.sprint_number === 3 ? 'bg-venom-amber/10' :
                'bg-krait-surface2'
              )}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-text-tertiary">
                    Sprint {sprint.sprint_number}
                  </span>
                  <span className="text-[10px] text-text-secondary">{sprint.estimated_hours}h</span>
                </div>
                <p className="text-[11px] font-semibold text-foreground mt-0.5">{sprint.title}</p>
              </div>
              <div className="p-3 space-y-2">
                {sprint.objectives.map((obj, i) => (
                  <p key={i} className="text-[10px] text-text-secondary leading-relaxed">
                    <Target className="w-3 h-3 inline-block mr-1 text-venom-yellow/70" />
                    {obj}
                  </p>
                ))}
                {sprint.tasks.length > 0 && (
                  <div className="border-t border-border pt-2 mt-2">
                    <p className="text-[9px] text-text-tertiary uppercase tracking-wider mb-1">Tasks</p>
                    <div className="space-y-1">
                      {sprint.tasks.slice(0, 4).map((task, i) => (
                        <p key={i} className="text-[10px] text-text-tertiary truncate">
                          <CheckCircle className="w-2.5 h-2.5 inline-block mr-1 text-text-tertiary" />
                          {task}
                        </p>
                      ))}
                      {sprint.tasks.length > 4 && (
                        <p className="text-[9px] text-text-tertiary">+{sprint.tasks.length - 4} more</p>
                      )}
                    </div>
                  </div>
                )}
                <div className="flex items-center justify-between pt-1 border-t border-border">
                  <span className="text-[10px] text-text-tertiary">Score gain</span>
                  <span className="text-[11px] font-semibold text-venom-yellow">+{sprint.expected_score_gain}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

export function OwnershipSection({
  data,
}: {
  data: OwnershipAssignment[] | null | undefined;
}) {
  if (!data || data.length === 0) return null;

  return (
    <SectionCard>
      <SectionHeader title="Recommended Ownership" />
      <SectionBody>
        <div className="divide-y divide-border/50">
          {data.map((item) => (
            <div key={item.recommended_team} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <Users className="w-4 h-4 shrink-0 text-text-tertiary" />
                <div>
                  <p className="text-[12px] font-medium text-foreground">{item.recommended_team}</p>
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {item.categories.slice(0, 4).map((cat) => (
                      <span key={cat} className="text-[9px] px-1 py-0.5 rounded bg-krait-surface2 text-text-tertiary">
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="text-right shrink-0 ml-3">
                <p className="text-[13px] font-semibold text-foreground">{item.total_findings}</p>
                <p className="text-[9px] text-text-tertiary">{item.estimated_hours}h</p>
              </div>
            </div>
          ))}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

export function AIRecommendationsSection({
  data,
}: {
  data: AIRecommendation[] | null | undefined;
}) {
  if (!data || data.length === 0) return null;

  return (
    <SectionCard>
      <SectionHeader title="AI Recommendations" badge={
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-venom-yellow/10 text-venom-yellow font-medium">
          AI-Powered
        </span>
      } />
      <SectionBody className="space-y-3">
        {data.map((rec) => (
          <div
            key={rec.cluster_id}
            className="rounded-lg border border-border bg-krait-surface1/30 overflow-hidden"
          >
            <div className="flex items-start justify-between px-4 py-2.5 border-b border-border bg-krait-surface1/20">
              <div className="min-w-0 flex-1">
                <p className="text-[12px] font-medium text-foreground truncate">{rec.problem}</p>
                <p className="text-[10px] text-text-tertiary">{rec.cluster_id}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-3">
                <span className={cn(
                  'text-[9px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wider',
                  rec.ai_confidence === 'high' ? 'bg-green-500/10 text-green-400' :
                  rec.ai_confidence === 'medium' ? 'bg-venom-amber/10 text-venom-amber' :
                  'bg-krait-surface2 text-text-tertiary'
                )}>
                  {rec.ai_confidence}
                </span>
              </div>
            </div>
            <div className="px-4 py-3 space-y-2">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-[11px] font-semibold text-venom-yellow">+{rec.expected_score_gain}</p>
                  <p className="text-[9px] text-text-tertiary">Score Gain</p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-foreground">{rec.estimated_hours}h</p>
                  <p className="text-[9px] text-text-tertiary">Effort</p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-text-secondary capitalize">
                    {rec.business_impact.split(' — ')[0]?.toLowerCase() ?? 'medium'}
                  </p>
                  <p className="text-[9px] text-text-tertiary">Impact</p>
                </div>
              </div>
              <div>
                <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-0.5">Root Cause</p>
                <p className="text-[11px] text-text-secondary leading-relaxed">{rec.root_cause}</p>
              </div>
              <div>
                <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-0.5">Enterprise Best Practice</p>
                <p className="text-[11px] text-venom-yellow/80 leading-relaxed">{rec.enterprise_best_practice}</p>
              </div>
              {rec.recommended_refactor && (
                <div>
                  <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-0.5">Recommended Refactor</p>
                  <p className="text-[11px] text-text-secondary leading-relaxed">{rec.recommended_refactor}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </SectionBody>
    </SectionCard>
  );
}

export function QuickWinsSection({
  data,
}: {
  data: QuickWin[] | null | undefined;
}) {
  if (!data || data.length === 0) return null;

  return (
    <SectionCard>
      <SectionHeader
        title="Quick Wins"
        badge={
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 font-medium">
            &lt;30 min each
          </span>
        }
      />
      <SectionBody>
        <div className="divide-y divide-border/50">
          {data.map((win, i) => (
            <div key={i} className="flex items-center justify-between py-2 first:pt-0 last:pb-0">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <SeverityLabel severity={win.priority} />
                  <span className="text-[12px] text-foreground truncate">{win.title}</span>
                </div>
                <p className="text-[10px] text-text-tertiary font-mono truncate mt-0.5">{win.file}</p>
              </div>
              <div className="flex items-center gap-3 shrink-0 ml-3">
                <span className="text-[10px] text-text-secondary">{win.estimated_time}m</span>
                <span className="text-[10px] text-venom-yellow">+{win.expected_score_improvement}</span>
              </div>
            </div>
          ))}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

export function ServiceHealthSection({
  data,
}: {
  data: Record<string, ServiceHealth> | null | undefined;
}) {
  if (!data || Object.keys(data).length === 0) return null;

  return (
    <SectionCard>
      <SectionHeader title="Service Health" />
      <SectionBody>
        <div className="divide-y divide-border/50">
          {Object.entries(data).map(([service, health]) => (
            <div key={service} className="py-3 first:pt-0 last:pb-0">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <StatusDot status={health.health_score >= 75 ? 'good' : health.health_score >= 50 ? 'needs_work' : 'critical'} />
                  <span className="text-[12px] font-medium text-foreground">{service}</span>
                </div>
                <div className="flex items-center gap-2">
                  <GradeBadge grade={health.grade} />
                  <span className="text-[16px] font-bold text-foreground">{health.health_score}</span>
                </div>
              </div>
              <HealthBar score={health.health_score} className="mb-2" />
              <div className="flex flex-wrap gap-1.5">
                {[
                  { label: 'Security', count: health.security },
                  { label: 'Perf', count: health.performance },
                  { label: 'Reliability', count: health.reliability },
                  { label: 'Maint', count: health.maintainability },
                ].map((dim) => (
                  <span
                    key={dim.label}
                    className={cn(
                      'text-[9px] px-1.5 py-0.5 rounded',
                      dim.count > 10 ? 'bg-red-500/10 text-red-400' :
                      dim.count > 3 ? 'bg-venom-amber/10 text-venom-amber' :
                      'bg-krait-surface2 text-text-tertiary'
                    )}
                  >
                    {dim.label}: {dim.count}
                  </span>
                ))}
                {health.critical_count > 0 && (
                  <span className="text-[9px] bg-red-500/15 text-red-400 px-1.5 py-0.5 rounded font-medium">
                    {health.critical_count} critical
                  </span>
                )}
              </div>
              <p className="text-[10px] text-text-tertiary mt-1">{health.recommendation}</p>
            </div>
          ))}
        </div>
      </SectionBody>
    </SectionCard>
  );
}

export function DeploymentReleaseSection({
  deployment,
  release,
}: {
  deployment: Record<string, unknown> | null | undefined;
  release: Record<string, unknown> | null | undefined;
}) {
  if (!deployment && !release) return null;

  return (
    <SectionCard>
      <SectionHeader title="Deployment & Release" />
      <SectionBody>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {deployment && (
            <div className="rounded-lg border border-border bg-krait-surface1/30 p-4">
              <h3 className="text-[12px] font-semibold text-foreground mb-3">Deployment Readiness</h3>
              <div className="flex items-center gap-2 mb-3">
                <StatusDot status={deployment.status as string} />
                <span className={cn(
                  'text-[13px] font-semibold capitalize',
                  deployment.status === 'ready' ? 'text-green-400' :
                  deployment.status === 'conditional' ? 'text-venom-amber' :
                  'text-red-400'
                )}>
                  {(deployment.status as string)?.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="space-y-1.5">
                {['security_check', 'performance_check', 'reliability_check', 'maintainability_check'].map((check) => (
                  <div key={check} className="flex items-center justify-between text-[11px]">
                    <span className="text-text-secondary capitalize">{check.replace(/_/g, ' ')}</span>
                    <span className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded font-medium',
                      (deployment[check] as string) === 'passed' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                    )}>
                      {deployment[check] as string}
                    </span>
                  </div>
                ))}
              </div>
              {(deployment.recommendation as string | undefined) && (
                <p className="text-[11px] text-text-tertiary mt-3 border-t border-border pt-3">
                  {deployment.recommendation as string}
                </p>
              )}
            </div>
          )}
          {release && (
            <div className="rounded-lg border border-border bg-krait-surface1/30 p-4">
              <h3 className="text-[12px] font-semibold text-foreground mb-3">Release Recommendation</h3>
              <div className="flex items-center gap-2 mb-3">
                <StatusDot status={release.decision as string} />
                <span className={cn(
                  'text-[13px] font-semibold capitalize',
                  release.decision === 'go' ? 'text-green-400' :
                  release.decision === 'proceed_with_caution' ? 'text-venom-amber' :
                  'text-red-400'
                )}>
                  {(release.decision as string)?.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3">
                {['grade', 'security_grade', 'performance_grade', 'reliability_grade'].map((g) => (
                  <div key={g} className="flex items-center justify-between text-[11px]">
                    <span className="text-text-tertiary capitalize">{g.replace(/_/g, ' ')}</span>
                    <span className="text-foreground font-semibold">{release[g] as string ?? 'N/A'}</span>
                  </div>
                ))}
              </div>
              {(release.description as string | undefined) && (
                <p className="text-[11px] text-text-tertiary border-t border-border pt-3">
                  {release.description as string}
                </p>
              )}
            </div>
          )}
        </div>
      </SectionBody>
    </SectionCard>
  );
}
