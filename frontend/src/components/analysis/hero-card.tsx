'use client';

import { useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus, Clock, Cpu, Files } from 'lucide-react';
import { ScoreGauge } from '@/components/analysis/score-gauge';
import type { Report, ScoreHistoryEntry, AnalysisJob } from '@/types/domain/analysis';

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '\u2014';
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

export function HeroCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-xl p-6 grid grid-cols-1 md:grid-cols-[auto_1fr_auto] gap-6 items-center animate-fade-up">
      <div className="w-40 h-40 rounded-full bg-surface2 animate-shimmer mx-auto" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
      <div className="space-y-3 mx-auto md:mx-0">
        <div className="h-5 w-48 rounded bg-surface2 animate-shimmer mx-auto md:mx-0" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
        <div className="h-4 w-64 rounded bg-surface2 animate-shimmer mx-auto md:mx-0" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
        <div className="h-3 w-40 rounded bg-surface2 animate-shimmer mx-auto md:mx-0" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />
      </div>
      <div className="grid grid-cols-2 gap-3 min-w-[200px]">
        {[1,2,3,4].map(i => <div key={i} className="h-14 rounded-lg bg-surface2 animate-shimmer" style={{ backgroundImage: 'linear-gradient(90deg, transparent, hsl(var(--krait-surface-3)/0.5), transparent)', backgroundSize: '200% 100%' }} />)}
      </div>
    </div>
  );
}

export function HeroCard({
  overallScore,
  report,
  scoreHistory,
  job,
}: {
  overallScore: number;
  report?: Report | null;
  scoreHistory?: ScoreHistoryEntry[];
  job: AnalysisJob;
}) {
  const sorted = useMemo(() => {
    if (!scoreHistory?.length) return null;
    return [...scoreHistory].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
  }, [scoreHistory]);

  const scoreChange = sorted && sorted.length >= 2 ? sorted[sorted.length - 1].overall_score - sorted[0].overall_score : null;

  const duration = report?.duration_seconds ?? null;
  const enginesCompleted = Object.values(job.engine_statuses ?? {}).filter(s => s === 'completed').length;
  const totalEngines = Object.keys(job.engine_statuses ?? {}).length || 5;
  const filesScanned = report?.total_files ?? job.total_files;

  return (
    <div className="bg-card border border-border rounded-xl p-6 grid grid-cols-1 md:grid-cols-[auto_1fr_auto] gap-6 items-center animate-fade-up">
      <ScoreGauge score={overallScore} size={160} strokeWidth={12} />

      <div className="text-center md:text-left">
        <p className="text-sm font-medium text-foreground mb-1">
          {overallScore >= 90 && 'Production Ready'}
          {overallScore >= 75 && overallScore < 90 && 'Minor Issues'}
          {overallScore >= 60 && overallScore < 75 && 'Needs Work'}
          {overallScore >= 40 && overallScore < 60 && 'Significant Risk'}
          {overallScore < 40 && 'Critical State'}
        </p>
        <p className="text-[13px] text-text-secondary leading-relaxed max-w-md">
          {overallScore >= 90 && 'Strong performance across all engines. No critical issues detected.'}
          {overallScore >= 75 && overallScore < 90 && 'Good overall quality with minor improvements recommended.'}
          {overallScore >= 60 && overallScore < 75 && 'Several areas require attention to meet production standards.'}
          {overallScore >= 40 && overallScore < 60 && 'Significant risks identified. Immediate action recommended.'}
          {overallScore < 40 && 'Critical vulnerabilities detected. Address high-severity issues first.'}
        </p>
        <div className="flex items-center justify-center md:justify-start gap-4 mt-3 text-[12px] text-text-tertiary">
          <span>{job.branch}</span>
          {job.repo_url && <span>{job.repo_url.replace('https://github.com/', '')}</span>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 min-w-[180px]">
        {scoreChange != null && (
          <div className="bg-background rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-0.5">
              {scoreChange > 0 ? (
                <TrendingUp className="w-4 h-4 text-green-400" />
              ) : scoreChange < 0 ? (
                <TrendingDown className="w-4 h-4 text-red-400" />
              ) : (
                <Minus className="w-4 h-4 text-text-tertiary" />
              )}
              <span className={`text-lg font-semibold tabular-nums ${scoreChange > 0 ? 'text-green-400' : scoreChange < 0 ? 'text-red-400' : 'text-text-tertiary'}`}>
                {scoreChange > 0 ? '+' : ''}{scoreChange}
              </span>
            </div>
            <p className="text-[10px] text-text-tertiary uppercase tracking-wider">vs first run</p>
          </div>
        )}
        <div className="bg-background rounded-lg p-3 text-center">
          <Clock className="w-4 h-4 text-venom-yellow mx-auto mb-0.5" />
          <p className="text-lg font-semibold text-foreground tabular-nums">{formatDuration(duration)}</p>
          <p className="text-[10px] text-text-tertiary uppercase tracking-wider">Duration</p>
        </div>
        <div className="bg-background rounded-lg p-3 text-center">
          <Cpu className="w-4 h-4 text-blue-400 mx-auto mb-0.5" />
          <p className="text-lg font-semibold text-foreground tabular-nums">{enginesCompleted}/{totalEngines}</p>
          <p className="text-[10px] text-text-tertiary uppercase tracking-wider">Engines</p>
        </div>
        <div className="bg-background rounded-lg p-3 text-center">
          <Files className="w-4 h-4 text-purple-400 mx-auto mb-0.5" />
          <p className="text-lg font-semibold text-foreground tabular-nums">{filesScanned ?? '\u2014'}</p>
          <p className="text-[10px] text-text-tertiary uppercase tracking-wider">Files</p>
        </div>
      </div>
    </div>
  );
}
