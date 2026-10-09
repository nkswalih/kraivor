import { Skeleton } from '@/components/ui/shadcn/skeleton';

/**
 * Loading states for the settings panel.
 *
 * Two different waits look identical to the person waiting -- the section's JS
 * chunk arriving, and its data coming back from the API -- so both paint the
 * same shimmer shapes instead of a spinner. A spinner says "something is
 * happening, sit tight"; a skeleton says "here is roughly what is coming",
 * which is the difference between a panel that feels instant and one that
 * feels like it stalled.
 */

/** Fallback while a section's code is still downloading. */
export function SectionSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-3 w-56" />
        <Skeleton className="h-3 w-40" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton variant="rect" className="h-24 w-full" />
        <Skeleton className="h-8 w-32" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-3 w-32" />
        <Skeleton variant="rect" className="h-16 w-full" />
        <Skeleton variant="rect" className="h-16 w-full" />
      </div>
    </div>
  );
}

/**
 * A bordered list of rows -- members, invitations, sessions, API keys. The
 * proportions mirror the real rows (36px avatar, two lines of text, a pill on
 * the right) so nothing jumps when the data lands.
 */
export function ListSkeleton({
  rows = 3,
  avatar = true,
}: {
  rows?: number;
  avatar?: boolean;
}) {
  return (
    <div className="border border-krait-border rounded-xl overflow-hidden divide-y divide-krait-border">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-5 py-3.5">
          {avatar && <Skeleton variant="circle" className="w-9 h-9 shrink-0" />}
          <div className="flex-1 min-w-0 space-y-1.5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-28" />
          </div>
          <Skeleton className="h-5 w-16 shrink-0" />
        </div>
      ))}
    </div>
  );
}

/** A whole form page: banner, avatar, a few fields, a save button. */
export function FormSkeleton() {
  return (
    <div className="space-y-8">
      <Skeleton variant="rect" className="h-32 w-full" />
      <div className="flex items-end gap-4 -mt-16 pl-4">
        <Skeleton variant="circle" className="w-20 h-20 ring-4 ring-krait-obsidian" />
      </div>
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton variant="rect" className="h-9 w-full max-w-[420px]" />
          </div>
        ))}
        <Skeleton variant="rect" className="h-9 w-28" />
      </div>
    </div>
  );
}
