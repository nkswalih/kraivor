'use client';

import { useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus, Loader2, AlertCircle, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ScoreHistoryEntry } from '@/types/domain/analysis';

function formatAxisDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatTooltipDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface ChartPoint {
  x: number;
  y: number;
  label: string;
  tooltip: string;
  score: number;
}

export function ScoreHistoryChart({
  entries,
  isLoading,
  error,
  className,
}: {
  entries: ScoreHistoryEntry[];
  isLoading: boolean;
  error?: Error | null;
  className?: string;
}) {
  const chartData = useMemo(() => {
    if (!entries.length) return null;
    const sorted = [...entries].sort(
      (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
    );
    const points: ChartPoint[] = sorted.map(e => ({
      x: new Date(e.time).getTime(),
      y: e.overall_score,
      label: formatAxisDate(e.time),
      tooltip: formatTooltipDate(e.time),
      score: e.overall_score,
    }));
    return points;
  }, [entries]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40 bg-card border border-border rounded-lg">
        <Loader2 className="w-5 h-5 text-venom-yellow animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-40 bg-card border border-border rounded-lg gap-2 text-text-tertiary">
        <AlertCircle className="w-4 h-4 text-red-400" />
        <span className="text-[12px]">Failed to load score history</span>
      </div>
    );
  }

  if (!chartData || chartData.length < 1) {
    return (
      <div className="flex flex-col items-center justify-center h-40 bg-card border border-border rounded-lg gap-2 text-text-tertiary">
        <BarChart3 className="w-5 h-5" />
        <span className="text-[12px]">No score history yet</span>
        <span className="text-[11px] text-text-tertiary/60">
          Scores appear here after each analysis
        </span>
      </div>
    );
  }

  const trend = chartData.length >= 2
    ? chartData[chartData.length - 1].score - chartData[0].score
    : 0;

  const width = 400;
  const height = 140;
  const padding = { top: 16, right: 8, bottom: 24, left: 32 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const xMin = chartData[0].x;
  const xMax = chartData[chartData.length - 1].x;
  const xRange = xMax - xMin || 1;
  const yMin = Math.max(0, Math.min(...chartData.map(p => p.y)) - 10);
  const yMax = Math.min(100, Math.max(...chartData.map(p => p.y)) + 10);
  const yRange = yMax - yMin || 1;

  const toX = (x: number) => padding.left + ((x - xMin) / xRange) * plotW;
  const toY = (y: number) => padding.top + plotH - ((y - yMin) / yRange) * plotH;

  const linePath = chartData
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${toX(p.x).toFixed(1)},${toY(p.y).toFixed(1)}`)
    .join(' ');

  const areaPath = `${linePath}L${toX(chartData[chartData.length - 1].x)},${toY(yMin)}L${toX(chartData[0].x)},${toY(yMin)}Z`;

  const yTicks = [0, 25, 50, 75, 100].filter(y => y >= yMin && y <= yMax);

  const latestScore = chartData[chartData.length - 1].score;
  const latestColor = latestScore >= 75 ? '#22c55e' : latestScore >= 50 ? '#eab308' : '#ef4444';

  return (
    <div className={cn('bg-card border border-border rounded-lg p-4', className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-medium text-foreground flex items-center gap-1.5">
          <BarChart3 className="w-4 h-4 text-blue-400" />
          Score Trend
        </h3>
        {chartData.length >= 2 && (
          <div className="flex items-center gap-1 text-[11px]">
            {trend > 0 && (
              <>
                <TrendingUp className="w-3.5 h-3.5 text-green-400" />
                <span className="text-green-400 font-medium">+{trend}</span>
              </>
            )}
            {trend < 0 && (
              <>
                <TrendingDown className="w-3.5 h-3.5 text-red-400" />
                <span className="text-red-400 font-medium">{trend}</span>
              </>
            )}
            {trend === 0 && (
              <>
                <Minus className="w-3.5 h-3.5 text-text-tertiary" />
                <span className="text-text-tertiary">0</span>
              </>
            )}
            <span className="text-text-tertiary ml-1">since first</span>
          </div>
        )}
      </div>

      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible"
          style={{ maxHeight: height + 20 }}
        >
          <defs>
            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={latestColor} stopOpacity="0.2" />
              <stop offset="100%" stopColor={latestColor} stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {yTicks.map(y => (
            <g key={y}>
              <line
                x1={padding.left}
                y1={toY(y)}
                x2={width - padding.right}
                y2={toY(y)}
                stroke="hsl(var(--krait-border))"
                strokeWidth="0.5"
                strokeDasharray="3 3"
                opacity="0.5"
              />
              <text
                x={padding.left - 6}
                y={toY(y) + 3}
                textAnchor="end"
                fill="hsl(var(--text-tertiary))"
                fontSize="9"
                fontFamily="monospace"
              >
                {y}
              </text>
            </g>
          ))}

          <path d={areaPath} fill="url(#areaGrad)" />

          <path
            d={linePath}
            fill="none"
            stroke={latestColor}
            strokeWidth="1.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {chartData.map((p, i) => (
            <g key={i}>
              <circle
                cx={toX(p.x)}
                cy={toY(p.y)}
                r={i === chartData.length - 1 ? 3 : 2}
                fill={i === chartData.length - 1 ? latestColor : 'hsl(var(--card))'}
                stroke={latestColor}
                strokeWidth="1.5"
                className="transition-all duration-300"
              />
              <title>{`${p.tooltip}\nScore: ${p.score}`}</title>
            </g>
          ))}

          {chartData.length > 1 &&
            chartData
              .filter((_, i) => i === 0 || i === chartData.length - 1 || i % Math.max(1, Math.floor(chartData.length / 5)) === 0)
              .map((p, i) => (
                <text
                  key={i}
                  x={toX(p.x)}
                  y={height - 4}
                  textAnchor="middle"
                  fill="hsl(var(--text-tertiary))"
                  fontSize="8"
                  fontFamily="monospace"
                >
                  {p.label}
                </text>
              ))}
        </svg>
      </div>
    </div>
  );
}
