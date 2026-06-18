'use client';

import { Sparkles, Loader2, AlertTriangle, Lightbulb, GitMerge } from 'lucide-react';
import { useAIRecommendations } from '@/lib/hooks/use-projects';

export function ProjectInsightsTab({ workspaceId, projectId }: { workspaceId: string; projectId: string }) {
  const { data: recommendations, isLoading } = useAIRecommendations(workspaceId, projectId);

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div className="flex items-center gap-2">
        <Sparkles size={16} className="text-[var(--venom-yellow)]" />
        <h2 className="text-[14px] font-medium text-[var(--text-primary)]">AI Insights</h2>
        <span className="text-[11px] text-[var(--text-tertiary)] border border-[var(--krait-border)] px-1.5 py-0.5 rounded ml-auto">
          {recommendations?.phase ?? 'Phase 2'}
        </span>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={20} className="animate-spin text-[var(--venom-yellow)]" />
        </div>
      )}

      {recommendations && (
        <div className="space-y-4">
          {recommendations.suggested_tasks.length > 0 && (
            <InsightGroup
              icon={<Lightbulb size={14} />}
              title="Suggested Tasks"
              items={recommendations.suggested_tasks}
            />
          )}

          {recommendations.blocked_risk.length > 0 && (
            <InsightGroup
              icon={<AlertTriangle size={14} />}
              title="Blocked Risk"
              items={recommendations.blocked_risk}
            />
          )}

          {recommendations.suggested_dependencies.length > 0 && (
            <InsightGroup
              icon={<GitMerge size={14} />}
              title="Suggested Dependencies"
              items={recommendations.suggested_dependencies}
            />
          )}

          {recommendations.suggested_tasks.length === 0 &&
            recommendations.blocked_risk.length === 0 &&
            recommendations.suggested_dependencies.length === 0 && (
            <div className="flex items-center gap-3 bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[8px] px-4 py-3">
              <Sparkles size={14} className="text-[var(--venom-yellow)] shrink-0" />
              <span className="text-[13px] text-[var(--text-secondary)]">
                No insights available yet. Add more tasks and dependencies to see AI-powered suggestions.
              </span>
            </div>
          )}

          <p className="text-[11px] text-[var(--text-tertiary)] text-right">
            Generated at {new Date(recommendations.generated_at).toLocaleString()}
          </p>
        </div>
      )}

      {!isLoading && !recommendations && (
        <div className="space-y-3">
          {['Blocked task detection', 'Story point estimation', 'Dependency suggestions', 'Sprint retrospective'].map((feature) => (
            <div
              key={feature}
              className="flex items-center gap-3 bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[8px] px-4 py-3"
            >
              <Sparkles size={14} className="text-[var(--text-tertiary)] shrink-0" />
              <span className="text-[13px] text-[var(--text-secondary)]">{feature}</span>
              <span className="ml-auto text-[11px] text-[var(--text-tertiary)]">Coming soon</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InsightGroup({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: unknown[];
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider mb-2">
        {icon}
        {title}
      </div>
      <div className="space-y-1">
        {items.map((item, i) => (
          <div
            key={i}
            className="bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[6px] px-3.5 py-2 text-[13px] text-[var(--text-secondary)]"
          >
            {String(item)}
          </div>
        ))}
      </div>
    </div>
  );
}
