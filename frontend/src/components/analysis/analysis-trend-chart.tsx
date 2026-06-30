'use client';

import { useMemo, useRef, useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, Minus, BarChart3 } from 'lucide-react';
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

function smoothPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return '';
  if (points.length === 2) {
    return `M${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}L${points[1].x.toFixed(1)},${points[1].y.toFixed(1)}`;
  }
  let d = `M${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    const p0 = points[Math.max(0, i - 2)];
    const p1 = points[i - 1];
    const p2 = points[i];
    const p3 = points[Math.min(points.length - 1, i + 1)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += `C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }
  return d;
}

function TrendChartSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="flex gap-2 mb-4">
        {[1,2,3,4].map(i => <div key={i} className="h-6 w-16 rounded-lg bg-surface2" />)}
      </div>
      <div className="h-48 rounded-xl bg-surface2" />
    </div>
  );
}

function TrendChartEmpty() {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3 text-text-tertiary">
      <BarChart3 className="w-10 h-10 opacity-30" />
      <div className="text-center">
        <p className="text-[13px] font-medium text-foreground mb-1">No historical trend available</p>
        <p className="text-[12px] text-text-tertiary max-w-xs">
          Run additional analyses to build repository trends over time.
        </p>
      </div>
    </div>
  );
}

export function AnalysisTrendChart({
  entries,
  isLoading,
  error,
  className,
  timeRange,
  onTimeRangeChange,
}: {
  entries: ScoreHistoryEntry[];
  isLoading: boolean;
  error?: Error | null;
  className?: string;
  timeRange: '7d' | '30d' | '90d' | 'all';
  onTimeRangeChange: (range: '7d' | '30d' | '90d' | 'all') => void;
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [animated, setAnimated] = useState(false);
  const pathRef = useRef<SVGPathElement>(null);
  const [pathLength, setPathLength] = useState(0);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    setAnimated(false);
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, [entries]);

  const chartData = useMemo(() => {
    if (!entries.length) return null;
    const sorted = [...entries]
      .filter(e => e.overall_score != null)
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

    if (sorted.length === 0) return null;

    if (sorted.length === 1) {
      const score = sorted[0].overall_score;
      const now = Date.now();
      const day = 86400000;
      return [
        { x: now - 7 * day, y: score, label: 'This Week', tooltip: `This Week\nScore: ${score}`, score, iso: sorted[0].time },
        { x: now - day, y: score, label: 'Yesterday', tooltip: `Yesterday\nScore: ${score}`, score, iso: sorted[0].time },
        { x: now, y: score, label: 'Today', tooltip: `Today\nScore: ${score}`, score, iso: sorted[0].time },
      ];
    }

    return sorted.map(e => ({
      x: new Date(e.time).getTime(),
      y: e.overall_score,
      label: formatAxisDate(e.time),
      tooltip: formatTooltipDate(e.time),
      score: e.overall_score,
      iso: e.time,
    }));
  }, [entries]);

  useEffect(() => {
    if (pathRef.current) {
      const len = pathRef.current.getTotalLength();
      setPathLength(len);
    }
  }, [chartData]);

  const TIME_OPTIONS = [
    { value: '7d' as const, label: '7 Days' },
    { value: '30d' as const, label: '30 Days' },
    { value: '90d' as const, label: '90 Days' },
    { value: 'all' as const, label: 'All Time' },
  ];

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!chartData || chartData.length < 2 || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const svgWidth = rect.width;
    const width = 500;
    const padding = { top: 20, right: 16, bottom: 28, left: 40 };
    const plotW = width - padding.left - padding.right;
    const xMin = chartData[0].x;
    const xMax = chartData[chartData.length - 1].x;
    const xRange = xMax - xMin || 1;
    const scaleX = svgWidth / width;
    const chartMouseX = (mouseX / scaleX);
    const dataX = xMin + ((chartMouseX - padding.left) / plotW) * xRange;
    let closest = 0;
    let minDist = Infinity;
    chartData.forEach((p, i) => {
      const dist = Math.abs(p.x - dataX);
      if (dist < minDist) { minDist = dist; closest = i; }
    });
    setHoveredIndex(closest);
  }, [chartData]);

  const handleMouseLeave = useCallback(() => {
    setHoveredIndex(null);
  }, []);

  if (isLoading) return <TrendChartSkeleton />;
  if (error) return <TrendChartEmpty />;
  if (!chartData) return <TrendChartEmpty />;

  const trend = chartData.length >= 2
    ? chartData[chartData.length - 1].score - chartData[0].score
    : 0;

  const width = 500;
  const height = 180;
  const padding = { top: 20, right: 16, bottom: 28, left: 40 };
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

  const linePath = smoothPath(chartData.map(p => ({ x: toX(p.x), y: toY(p.y) })));
  const areaPath = chartData.length >= 2
    ? linePath + `L${toX(chartData[chartData.length - 1].x).toFixed(1)},${toY(yMin).toFixed(1)}L${toX(chartData[0].x).toFixed(1)},${toY(yMin).toFixed(1)}Z`
    : '';

  const yTicks = [0, 25, 50, 75, 100].filter(y => y >= yMin && y <= yMax);
  const BLUE = '#3b82f6';

  return (
    <div className={cn('space-y-4', className)}>
      {/* Time filter */}
      <div className="flex items-center justify-between">
        <div>
          {chartData.length >= 2 && (
            <div className="flex items-center gap-1.5 text-[12px]">
              {trend > 0 && (
                <><TrendingUp className="w-3.5 h-3.5 text-green-400" /><span className="text-green-400 font-medium">+{trend}</span></>
              )}
              {trend < 0 && (
                <><TrendingDown className="w-3.5 h-3.5 text-red-400" /><span className="text-red-400 font-medium">{trend}</span></>
              )}
              {trend === 0 && (
                <><Minus className="w-3.5 h-3.5 text-text-tertiary" /><span className="text-text-tertiary">0</span></>
              )}
              <span className="text-text-tertiary">pts since first scan</span>
            </div>
          )}
        </div>
        <div className="flex gap-1 bg-background rounded-lg p-0.5 border border-border">
          {TIME_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => onTimeRangeChange(opt.value)}
              className={cn(
                'px-2.5 py-1 text-[11px] rounded-md transition-all font-medium',
                timeRange === opt.value
                  ? 'bg-card text-foreground shadow-sm border border-border'
                  : 'text-text-tertiary hover:text-foreground border border-transparent'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible"
          style={{ maxHeight: height + 20 }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="trendArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={BLUE} stopOpacity="0.15" />
              <stop offset="100%" stopColor={BLUE} stopOpacity="0.01" />
            </linearGradient>
            <filter id="trendGlow">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="trendSoftGlow">
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Grid lines */}
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
                opacity="0.4"
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

          {/* Area fill */}
          {areaPath && (
            <path
              d={areaPath}
              fill="url(#trendArea)"
              style={{
                opacity: animated ? 1 : 0,
                transition: 'opacity 600ms ease-out',
              }}
            />
          )}

          {/* Glow line (behind) */}
          {linePath && (
            <path
              d={linePath}
              fill="none"
              stroke={BLUE}
              strokeWidth="6"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.15"
              filter="url(#trendSoftGlow)"
              style={{
                strokeDasharray: pathLength || 2000,
                strokeDashoffset: animated ? 0 : (pathLength || 2000),
                transition: 'stroke-dashoffset 900ms ease-out',
              }}
            />
          )}

          {/* Main line */}
          {linePath && (
            <path
              ref={pathRef}
              d={linePath}
              fill="none"
              stroke={BLUE}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter="url(#trendGlow)"
              style={{
                strokeDasharray: pathLength || 2000,
                strokeDashoffset: animated ? 0 : (pathLength || 2000),
                transition: 'stroke-dashoffset 900ms ease-out',
              }}
            />
          )}

          {/* Data points */}
          {chartData.map((p, i) => (
            <g key={i}>
              <circle
                cx={toX(p.x)}
                cy={toY(p.y)}
                r={i === chartData.length - 1 ? 4 : 2.5}
                fill={i === chartData.length - 1 ? BLUE : 'hsl(var(--card))'}
                stroke={BLUE}
                strokeWidth="2"
                style={{
                  opacity: animated ? 1 : 0,
                  transition: `opacity 300ms ${600 + i * 50}ms ease-out`,
                }}
              />
              {i === chartData.length - 1 && (
                <circle
                  cx={toX(p.x)}
                  cy={toY(p.y)}
                  r="8"
                  fill="none"
                  stroke={BLUE}
                  strokeWidth="1"
                  opacity="0.3"
                  style={{
                    opacity: animated ? 0.3 : 0,
                    transition: 'opacity 500ms 800ms ease-out',
                  }}
                />
              )}
              <title>{`${p.tooltip}\nScore: ${p.score}`}</title>
            </g>
          ))}

          {/* X-axis labels */}
          {chartData.length > 1 &&
            chartData
              .filter((_, i) => i === 0 || i === chartData.length - 1 || i % Math.max(1, Math.floor(chartData.length / 6)) === 0)
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

          {/* Crosshair */}
          {hoveredIndex != null && chartData.length > 1 && (
            <g>
              <line
                x1={toX(chartData[hoveredIndex].x)}
                y1={padding.top}
                x2={toX(chartData[hoveredIndex].x)}
                y2={height - padding.bottom}
                stroke={BLUE}
                strokeWidth="1"
                strokeDasharray="3 3"
                opacity="0.4"
              />
              <rect
                x={toX(chartData[hoveredIndex].x) + 8}
                y={toY(chartData[hoveredIndex].y) - 18}
                width="100"
                height="28"
                rx="4"
                fill="hsl(var(--card))"
                stroke="hsl(var(--border))"
                strokeWidth="0.5"
                opacity="0.95"
              />
              <text
                x={toX(chartData[hoveredIndex].x) + 14}
                y={toY(chartData[hoveredIndex].y) - 4}
                fill="hsl(var(--foreground))"
                fontSize="10"
                fontFamily="monospace"
                fontWeight="600"
              >
                {chartData[hoveredIndex].score}
              </text>
              <text
                x={toX(chartData[hoveredIndex].x) + 50}
                y={toY(chartData[hoveredIndex].y) - 4}
                fill="hsl(var(--text-tertiary))"
                fontSize="9"
                textAnchor="end"
              >
                {chartData[hoveredIndex].label}
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  );
}
