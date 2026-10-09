'use client';

/**
 * Loading states for the inbox panel.
 *
 * Three different waits look identical to the person waiting -- the section's
 * JS chunk arriving, its list coming back from the API, and a nested request
 * (room messages) resolving -- so all three paint the same shimmer shapes
 * instead of a spinner. A spinner says "something is happening, sit tight"; a
 * skeleton says "here is roughly what is coming", which is the difference
 * between a panel that feels instant and one that feels like it stalled.
 *
 * These use a swept gradient rather than `animate-pulse`: the inbox is dark
 * (`#111113` rows on `#0A0A0B`), and a pulsing block of near-black reads as a
 * rendering bug at that contrast. A highlight travelling across the row reads
 * as loading, and matches what Settings already does.
 */

const SHIMMER =
  'rounded animate-shimmer bg-gradient-to-r from-[#1B1B1F] via-[#2E2E33] to-[#1B1B1F] bg-[length:200%_100%]';

function Shimmer({ className = '' }: { className?: string }) {
  return <div className={`${SHIMMER} ${className}`} />;
}

/** One notification row: 40px avatar, a title, a line of body, a timestamp. */
export function InboxRowSkeleton() {
  return (
    <div className="flex gap-3 p-3 rounded-lg">
      <Shimmer className="w-9 h-9 rounded-full shrink-0" />
      <div className="flex-1 min-w-0 space-y-1.5 pt-1">
        <Shimmer className="h-3 w-2/5" />
        <Shimmer className="h-3 w-3/5" />
      </div>
      <Shimmer className="h-3 w-10 shrink-0 mt-1" />
    </div>
  );
}

/**
 * Fallback while a section's code is still downloading.
 *
 * Shaped like a split view because three of the five sections are one -- the
 * proportions land close to the real thing at every width, so the swap costs
 * no layout shift. On a narrow screen the detail pane is absent, which is
 * also what the real split shows before anything is selected.
 */
export function InboxSectionSkeleton() {
  return (
    <div className="flex flex-1 min-h-0 min-w-0 flex-col sm:flex-row">
      <div className="min-h-0 flex-1 w-full space-y-1 p-3 sm:flex-none sm:w-[320px] sm:shrink-0 border-b border-[#27272A] sm:border-b-0 sm:border-r">
        {Array.from({ length: 6 }).map((_, i) => (
          <InboxRowSkeleton key={i} />
        ))}
      </div>
      <div className="hidden sm:flex sm:flex-1 min-w-0 flex-col gap-3 p-4">
        <Shimmer className="h-4 w-40" />
        <Shimmer className="h-3 w-3/4" />
        <Shimmer className="h-3 w-2/3" />
        <Shimmer className="h-24 w-full" />
      </div>
    </div>
  );
}

/** The list half of a split view, on its own. */
export function InboxListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="p-3 space-y-1">
      {Array.from({ length: rows }).map((_, i) => (
        <InboxRowSkeleton key={i} />
      ))}
    </div>
  );
}

/** A list pane beside a detail pane, both still resolving. */
export function InboxSplitSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-1 min-h-0 min-w-0 flex-col sm:flex-row">
      <div className="min-h-0 flex-1 w-full sm:flex-none sm:w-[320px] sm:shrink-0 overflow-y-auto border-b border-[#27272A] sm:border-b-0 sm:border-r">
        <InboxListSkeleton rows={rows} />
      </div>
      <div className="hidden sm:flex sm:flex-1 min-w-0 flex-col gap-3 p-4">
        <div className="flex items-center gap-3">
          <Shimmer className="w-10 h-10 rounded-full shrink-0" />
          <div className="space-y-1.5">
            <Shimmer className="h-3.5 w-32" />
            <Shimmer className="h-3 w-20" />
          </div>
        </div>
        <Shimmer className="h-3 w-full" />
        <Shimmer className="h-3 w-5/6" />
        <Shimmer className="h-3 w-2/3" />
      </div>
    </div>
  );
}

/** A single stack of cards: invitations, member activity, direct messages. */
export function InboxCardSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 rounded-lg border border-[#27272A] bg-[#111113]">
          <Shimmer className="w-9 h-9 rounded-lg shrink-0" />
          <div className="flex-1 min-w-0 space-y-1.5">
            <Shimmer className="h-3 w-1/3" />
            <Shimmer className="h-3 w-1/2" />
          </div>
          <Shimmer className="h-7 w-16 shrink-0" />
        </div>
      ))}
    </div>
  );
}

/** Message bubbles under a selected channel. */
export function InboxMessagesSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <Shimmer className="w-8 h-8 rounded-full shrink-0" />
          <div className="flex-1 space-y-1.5 pt-1">
            <Shimmer className="h-3 w-24" />
            <Shimmer className="h-3 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}
