'use client';

import { Heart, TrendingUp, AlertTriangle } from 'lucide-react';
import type { HealthReport, KnowledgeStats } from '@/lib/api/knowledge-ai-api';

export function KnowledgeHealthCard({
  health,
  stats,
}: {
  health: HealthReport | undefined;
  stats: KnowledgeStats | undefined;
}) {
  if (!health) return null;

  const score = health.overall_health?.score ?? 0;
  const grade = health.overall_health?.grade ?? 'N/A';
  const breakdown = health.overall_health?.breakdown;

  const gradeColor =
    score >= 80 ? 'text-green-400' :
    score >= 60 ? 'text-yellow-400' :
    'text-red-400';

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Heart className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium">Health Score</h3>
      </div>

      {/* Score gauge */}
      <div className="flex items-center gap-4 mb-4">
        <div className="relative w-16 h-16">
          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
            <path
              className="text-border"
              stroke="currentColor"
              strokeWidth="3"
              fill="none"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              className={gradeColor}
              stroke="currentColor"
              strokeWidth="3"
              fill="none"
              strokeDasharray={`${score}, 100`}
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-lg font-bold ${gradeColor}`}>{grade}</span>
          </div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{score}</div>
          <div className="text-[11px] text-muted-foreground">Overall Score</div>
        </div>
      </div>

      {/* Breakdown bars */}
      {breakdown && (
        <div className="space-y-2">
          {Object.entries(breakdown).map(([key, value]) => (
            <div key={key}>
              <div className="flex justify-between text-[11px] mb-0.5">
                <span className="text-muted-foreground capitalize">{key}</span>
                <span className="text-foreground">{value}%</span>
              </div>
              <div className="h-1.5 bg-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-venom-yellow rounded-full transition-all"
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Gaps */}
      {health.gaps && health.gaps.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="flex items-center gap-1 text-[11px] text-yellow-400 mb-1">
            <AlertTriangle className="w-3 h-3" />
            {health.gaps.length} gap{health.gaps.length > 1 ? 's' : ''} detected
          </div>
          {health.gaps.slice(0, 2).map((gap, i) => (
            <div key={i} className="text-[11px] text-muted-foreground">
              {gap.topic} — {gap.recommendation}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
