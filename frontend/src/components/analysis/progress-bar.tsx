'use client';

import { cn } from '@/lib/utils';

export function ProgressBar({
  pct,
  message,
  label,
  className,
}: {
  pct: number;
  message?: string;
  /**
   * Accessible name for the bar. Defaults to `message`, which is what all three
   * callers pass, so the bar is never announced as an unlabelled percentage --
   * "62%" with nothing saying 62 of what.
   */
  label?: string;
  className?: string;
}) {
  const clamped = Math.min(100, Math.max(0, pct));
  const rounded = Math.round(clamped);
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {message && (
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-text-secondary">{message}</span>
          <span className="text-[12px] font-mono text-text-tertiary">{rounded}%</span>
        </div>
      )}
      {/* The value lives here, not only in the label row above. Without the role
          and the three `aria-value*` attributes this is two unlabelled divs with
          a width on one of them: the eye gets a fill and a number, a screen
          reader gets nothing at all. `aria-valuetext` spells the figure out with
          its unit rather than leaving it to be announced as a bare integer.

          The fill inside is a presentational child -- `progressbar` declares its
          children presentational -- so it is not read as content. */}
      <div
        role="progressbar"
        aria-valuenow={rounded}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={`${rounded}%`}
        aria-label={label ?? message}
        className="h-1.5 bg-krait-surface2 rounded-full overflow-hidden"
      >
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${clamped}%`,
            // The brand pair, previously the literal gradient `#eab308 → #f59e0b`.
            // Neither value was a project colour: `#eab308` is Tailwind's
            // `yellow-500` and `#f59e0b` only matched by coincidence. Naming the
            // tokens is what lets the two themes restyle this bar.
            background:
              'linear-gradient(90deg, var(--venom-yellow), var(--venom-amber))',
          }}
        />
      </div>
    </div>
  );
}
