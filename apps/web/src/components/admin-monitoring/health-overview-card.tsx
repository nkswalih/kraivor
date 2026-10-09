'use client';

import { Heart, TrendingUp, AlertTriangle } from 'lucide-react';
import type { HealthReport } from '@/lib/api/knowledge-ai-api';

export function HealthOverviewCard({ health }: { health: HealthReport | undefined }) {
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
        <h3 className="text-[13px] font-medium">Knowledge Health</h3>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className="relative w-14 h-14">
          <svg className="w-14 h-14 -rotate-90" viewBox="0 0 36 36">
            <path className="text-border" stroke="currentColor" strokeWidth="3" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path className={gradeColor} stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray={`${score}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
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

      {breakdown && (
        <div className="space-y-2">
          {Object.entries(breakdown).map(([key, value]) => (
            <div key={key}>
              <div className="flex justify-between text-[11px] mb-0.5">
                <span className="text-muted-foreground capitalize">{key}</span>
                <span className="text-foreground">{value}%</span>
              </div>
              <div className="h-1.5 bg-border rounded-full overflow-hidden">
                <div className="h-full bg-venom-yellow rounded-full" style={{ width: `${value}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {health.recommendations && health.recommendations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="text-[11px] text-muted-foreground mb-1">Recommendations</div>
          {health.recommendations.slice(0, 3).map((rec, i) => (
            <div key={i} className="text-[11px] text-foreground flex items-start gap-1">
              <TrendingUp className="w-3 h-3 text-venom-yellow mt-0.5 shrink-0" />
              {rec}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
