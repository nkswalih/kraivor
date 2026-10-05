'use client';

import { cn } from '@/lib/utils';

/**
 * Score bands, as palette classes rather than hex values.
 *
 * The ring is an SVG, so a Tailwind class cannot be put on the arc itself. It
 * can be put on an ancestor, because `stroke="currentColor"` takes the colour
 * from the element's own text colour -- which also colours the number inside the
 * ring, so one class covers both. This keeps the five bands in step with the
 * palette the rest of the app uses instead of a private copy of it, and lets the
 * theme change them without touching this file.
 */
const SCORE_BANDS: Array<{ min: number; className: string }> = [
  { min: 90, className: 'text-green-500' },
  { min: 75, className: 'text-blue-500' },
  { min: 60, className: 'text-yellow-500' },
  { min: 40, className: 'text-orange-500' },
];

/** The band a score falls in, or an empty string when there is no score. */
function bandClass(score: number | null | undefined): string {
  if (score == null) return '';
  const band = SCORE_BANDS.find((b) => score >= b.min);
  return band ? band.className : 'text-red-500';
}

export function ProgressRing({
  score,
  size = 48,
  strokeWidth = 4,
  label,
  className,
}: {
  score: number | null | undefined;
  size?: number;
  strokeWidth?: number;
  label?: string;
  className?: string;
}) {
  const band = bandClass(score);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = score != null ? Math.min(100, Math.max(0, score)) : 0;
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div className={cn('flex flex-col items-center gap-1', band, className)}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* The unfilled track. Previously `hsl(var(--krait-border))`, but
              `--krait-border` is a hex, not the three bare numbers `hsl()`
              needs -- so the value was invalid, the stroke was dropped, and the
              track behind the arc was invisible. */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--krait-border)"
            strokeWidth={strokeWidth}
          />
          {score != null && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              // The arc sweeps to its new length over a second. Same reasoning
              // as the bar's fill: a drawn edge travelling around the circle is
              // movement, so it arrives at once under reduced motion.
              className="transition-all duration-1000 ease-out motion-reduce:transition-none"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          {score != null ? (
            <span className="text-[11px] font-semibold tabular-nums">
              {score}
            </span>
          ) : (
            <span className="text-[9px] text-text-tertiary">N/A</span>
          )}
        </div>
      </div>
      {label && (
        <span className="text-[10px] text-text-tertiary uppercase tracking-wider text-center leading-tight">
          {label}
        </span>
      )}
    </div>
  );
}
