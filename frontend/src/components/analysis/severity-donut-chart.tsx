'use client';

import { useState, useEffect, useRef } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FindingsSummary } from '@/types/domain/analysis';

const SEGMENTS = [
  { key: 'critical', label: 'Critical', color: '#ef4444', glow: 'rgba(239,68,68,0.3)' },
  { key: 'high', label: 'High', color: '#f97316', glow: 'rgba(249,115,22,0.25)' },
  { key: 'medium', label: 'Medium', color: '#eab308', glow: 'rgba(234,179,8,0.2)' },
  { key: 'low', label: 'Low', color: '#3b82f6', glow: 'rgba(59,130,246,0.2)' },
];

function SeverityDonutSkeleton() {
  return (
    <div className="flex items-center justify-center h-48 gap-8 animate-pulse">
      <div className="w-40 h-40 rounded-full bg-surface2" />
      <div className="space-y-3">
        {[1,2,3,4].map(i => <div key={i} className="h-4 w-32 rounded bg-surface2" />)}
      </div>
    </div>
  );
}

function SeverityDonutEmpty() {
  return (
    <div className="flex flex-col items-center justify-center h-48 gap-3">
      <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center">
        <CheckCircle2 className="w-8 h-8 text-green-400" />
      </div>
      <div className="text-center">
        <p className="text-[13px] font-medium text-foreground mb-1">No Findings</p>
        <p className="text-[12px] text-text-tertiary">Excellent. No issues were detected during analysis.</p>
      </div>
    </div>
  );
}

export function SeverityDonutChart({
  summary,
  isLoading,
  error,
}: {
  summary: FindingsSummary | null | undefined;
  isLoading?: boolean;
  error?: Error | null;
}) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [animated, setAnimated] = useState(false);
  const [count, setCount] = useState(0);
  const prevTotalRef = useRef(0);

  useEffect(() => {
    setAnimated(false);
    const timer = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(timer);
  }, [summary]);

  useEffect(() => {
    if (!summary) return;
    const target = summary.total;
    const start = prevTotalRef.current;
    prevTotalRef.current = target;
    if (start === target) { setCount(target); return; }
    const duration = 600;
    const startTime = performance.now();
    const raf = requestAnimationFrame(function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(start + (target - start) * eased));
      if (progress < 1) requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(raf);
  }, [summary]);

  if (isLoading) return <SeverityDonutSkeleton />;
  if (error) return <SeverityDonutEmpty />;
  if (!summary || summary.total === 0) return <SeverityDonutEmpty />;

  const total = summary.total;
  const cx = 80, cy = 80, r = 62, sw = 16;
  const circumference = 2 * Math.PI * r;

  let cumulative = 0;
  const arcs: { key: string; label: string; color: string; glow: string; count: number; length: number; offset: number; pct: number }[] = [];
  for (const seg of SEGMENTS) {
    const cnt = summary.by_severity[seg.key] ?? 0;
    if (cnt === 0) continue;
    const pct = cnt / total;
    const length = pct * circumference;
    const offset = cumulative * circumference;
    cumulative += pct;
    arcs.push({ ...seg, count: cnt, length, offset, pct });
  }

  if (arcs.length === 0) return <SeverityDonutEmpty />;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-8">
      {/* Donut */}
      <div className="relative shrink-0">
        <svg width="160" height="160" viewBox="0 0 160 160" role="img" aria-label="Findings by severity donut chart">
          <title>Findings by severity: {arcs.map(s => s.label + ' ' + s.count + ' (' + (s.pct * 100).toFixed(0) + '%)').join(', ')}</title>

          <defs>
            {arcs.map(seg => (
              <filter key={seg.key} id={`glow-${seg.key}`}>
                <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            ))}
          </defs>

          <g transform="rotate(-90 80 80)">
            {arcs.map((seg, i) => {
              const isHovered = hoveredKey === null || hoveredKey === seg.key;
              const offset = animated ? -seg.offset : 0;
              const dashArray = animated
                ? `${Math.max(seg.length, 1)} ${Math.max(circumference - seg.length, 1)}`
                : `0 ${circumference}`;

              return (
                <circle
                  key={seg.key}
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill="none"
                  stroke={seg.color}
                  strokeWidth={sw}
                  strokeDasharray={dashArray}
                  strokeDashoffset={offset}
                  strokeLinecap="round"
                  opacity={isHovered ? 1 : 0.3}
                  filter={isHovered && hoveredKey !== null ? `url(#glow-${seg.key})` : undefined}
                  className="cursor-pointer transition-all duration-300"
                  onMouseEnter={() => setHoveredKey(seg.key)}
                  onMouseLeave={() => setHoveredKey(null)}
                  style={{
                    transition: 'stroke-dasharray 700ms ease-out, stroke-dashoffset 700ms ease-out, opacity 200ms ease-out',
                    transitionDelay: animated ? `${i * 120}ms` : '0ms',
                  }}
                />
              );
            })}
          </g>

          {/* Center text */}
          <text
            x={80}
            y={72}
            textAnchor="middle"
            fill="hsl(var(--foreground))"
            fontSize="28"
            fontWeight="700"
            fontFamily="monospace"
            style={{
              opacity: animated ? 1 : 0,
              transform: animated ? 'scale(1)' : 'scale(0.5)',
              transition: 'opacity 400ms 500ms ease-out, transform 400ms 500ms ease-out',
              transformOrigin: '80px 80px',
            }}
          >
            {count}
          </text>
          <text
            x={80}
            y={94}
            textAnchor="middle"
            fill="hsl(var(--text-tertiary))"
            fontSize="11"
            fontFamily="sans-serif"
            style={{
              opacity: animated ? 0.8 : 0,
              transition: 'opacity 400ms 600ms ease-out',
            }}
          >
            Total Findings
          </text>
        </svg>
      </div>

      {/* Legend */}
      <div className="space-y-3 w-full sm:w-auto min-w-[160px]">
        {arcs.map((seg, i) => {
          const isHovered = hoveredKey === null || hoveredKey === seg.key;
          return (
            <div
              key={seg.key}
              className={cn(
                'flex items-center gap-3 text-[12px] cursor-pointer transition-all duration-200',
                isHovered ? 'opacity-100' : 'opacity-40',
              )}
              onMouseEnter={() => setHoveredKey(seg.key)}
              onMouseLeave={() => setHoveredKey(null)}
              style={{
                transitionDelay: animated ? `${i * 80}ms` : '0ms',
                transform: animated ? 'translateY(0)' : 'translateY(8px)',
                opacity: animated ? (isHovered ? 1 : 0.4) : 0,
                transition: 'transform 400ms ease-out, opacity 400ms ease-out',
              }}
            >
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: seg.color, boxShadow: `0 0 6px ${seg.glow}` }}
              />
              <span className="text-text-secondary w-14">{seg.label}</span>
              <span className="text-foreground font-medium tabular-nums w-8 text-right">{seg.count}</span>
              <span className="text-text-tertiary tabular-nums w-12 text-right">({(seg.pct * 100).toFixed(0)}%)</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
