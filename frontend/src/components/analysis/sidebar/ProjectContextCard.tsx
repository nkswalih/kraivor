'use client';

import { useEffect, useState } from 'react';
import {
  Files,
  Code2,
  Braces,
  FunctionSquare,
  Route,
  Languages,
  Package,
  GitBranch,
  Globe,
  Building2,
  Hash,
  Activity,
  Clock,
  Calendar,
} from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import {
  CLONE_COMPLETE_PCT,
  PARSE_COMPLETE_PCT,
  PARSE_PROGRESSING_PCT,
  measure,
} from '@/lib/analysis/run-context';
import type { RunFact } from '@/lib/analysis/run-context';
import { JobStatus } from '@/types/domain/analysis';
import type { AnalysisJob, AnalysisMetadataResponse } from '@/types/domain/analysis';

export interface ProjectContextCardProps {
  job: AnalysisJob | null | undefined;
  /** The parse-stage metadata row, while a run is still producing one. */
  metadata?: AnalysisMetadataResponse | null;
  isLoading?: boolean;
  className?: string;
}

const STATUS_LABEL: Record<JobStatus, string> = {
  [JobStatus.QUEUED]: 'Queued',
  [JobStatus.CLONING]: 'Cloning',
  [JobStatus.PARSING]: 'Parsing',
  [JobStatus.RULES]: 'Rules',
  [JobStatus.DEAD_CODE]: 'Dead code',
  [JobStatus.ERRORS]: 'Errors',
  [JobStatus.PERF]: 'Performance',
  [JobStatus.SIMULATION]: 'Simulation',
  [JobStatus.SCORING]: 'Scoring',
  [JobStatus.GUIDE_GEN]: 'Writing guide',
  [JobStatus.COMPLETED]: 'Complete',
  [JobStatus.FAILED]: 'Failed',
};

/**
 * The run's own facts, and the repository's, as they are established.
 *
 * Every figure here is either real or visibly absent. There are no defaults and
 * no placeholders dressed as values: a count that has not been taken shows a
 * shimmering block, and the row beside it names the stage that will take it.
 */
export function ProjectContextCard({
  job,
  metadata,
  isLoading,
  className,
}: ProjectContextCardProps) {
  if (isLoading || !job) {
    return <Skeleton className={className} />;
  }

  // `job` is non-null from here: the loading case returned above.
  const progressPct = job.progress_pct ?? 0;
  const status = job.status;

  const files = measure(job.total_files, progressPct, CLONE_COMPLETE_PCT);
  const lines = measure(job.total_lines, progressPct, CLONE_COMPLETE_PCT);
  const languages = measure(job.languages_detected, progressPct, CLONE_COMPLETE_PCT);
  // Frameworks are detected during clone but reach the frontend with the
  // metadata row, which the parse stage starts writing at 25%. A zero here is a
  // real answer -- the detection ran and found none.
  const frameworks = measure(
    metadata?.frameworks == null ? null : metadata.frameworks.length,
    progressPct,
    PARSE_PROGRESSING_PCT,
  );

  // The parse stage recounts as it goes, so these are ready from the first
  // batch and only become settled once it finishes.
  const classes = measure(
    metadata?.class_count,
    progressPct,
    PARSE_PROGRESSING_PCT,
    PARSE_COMPLETE_PCT,
  );
  const functions = measure(
    metadata?.function_count,
    progressPct,
    PARSE_PROGRESSING_PCT,
    PARSE_COMPLETE_PCT,
  );
  const endpoints = measure(
    metadata?.endpoint_count,
    progressPct,
    PARSE_PROGRESSING_PCT,
    PARSE_COMPLETE_PCT,
  );

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <h3 className="text-[13px] font-semibold text-foreground mb-3">Project Context</h3>

      <section className="mb-3">
        <SectionLabel>Repository</SectionLabel>
        <div className="space-y-0.5">
          <Row
            icon={Globe}
            label="Repository"
            value={formatRepo(job.repo_url)}
            pendingText="Waiting for the clone"
          />
          <Row
            icon={GitBranch}
            label="Branch"
            value={job.branch ?? null}
            pendingText="Waiting for the clone"
          />
          <Row
            icon={Building2}
            label="Workspace"
            value={job.workspace_id ? job.workspace_id.slice(0, 8) : null}
            pendingText="Unknown until the job loads"
          />
        </div>
      </section>

      <section className="mb-3">
        <SectionLabel>This run</SectionLabel>
        <div className="space-y-0.5">
          <Row
            icon={Hash}
            label="Run"
            value={job.job_id ? job.job_id.slice(0, 8) : null}
            pendingText="Unknown until the job loads"
          />
          <Row
            icon={Activity}
            label="Status"
            value={status ? STATUS_LABEL[status] ?? status : null}
            pendingText="Unknown until the job loads"
            tone={status === JobStatus.FAILED ? 'danger' : undefined}
          />
          <ElapsedRow job={job} />
          <Row
            icon={Calendar}
            label="Started"
            value={
              usableTimestamp(job.started_at)
                ? formatRelativeTime(job.started_at as string)
                : null
            }
            pendingText="Once the run starts"
          />
        </div>
      </section>

      <section>
        <SectionLabel>Measured</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          <Fact
            icon={Files}
            iconClass="text-blue-400"
            label="Files"
            fact={files}
          />
          <Fact
            icon={Code2}
            iconClass="text-green-400"
            label="Lines"
            fact={lines}
          />
          <Fact
            icon={Braces}
            iconClass="text-purple-400"
            label="Classes"
            fact={classes}
          />
          <Fact
            icon={FunctionSquare}
            iconClass="text-cyan-400"
            label="Functions"
            fact={functions}
          />
          <Fact
            icon={Route}
            iconClass="text-amber-400"
            label="Endpoints"
            fact={endpoints}
          />
          <Fact
            icon={Package}
            iconClass="text-pink-400"
            label="Frameworks"
            fact={frameworks}
          />
        </div>

        <div className="mt-2 space-y-0.5">
          <Row
            icon={Languages}
            label="Languages"
            value={
              languages.state === 'ready' && languages.value.length > 0
                ? languages.value.join(', ')
                : null
            }
            pendingText={languages.state === 'ready' ? 'None detected' : 'Waiting for the clone'}
          />
        </div>
      </section>
    </div>
  );
}

/**
 * Placeholder for the whole card while the job itself is loading.
 *
 * Distinct from the per-fact placeholders below: here nothing is known at all,
 * not even which facts exist. The row count matches the settled card so the
 * panel below does not jump when the real one arrives.
 */
function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <div className="h-3.5 bg-krait-surface2 rounded animate-shimmer w-32 mb-4" />

      {/* Same three sections, same shapes as the settled card: two labelled row
          groups, then the tile grid with its trailing language row. Matching the
          shape rather than approximating it is what stops the cards below
          shifting when the real panel replaces this one. */}
      <div className="mb-3">
        <div className="h-2.5 bg-krait-surface2 rounded animate-shimmer w-16 mb-2" />
        <SkeletonRows count={3} />
      </div>
      <div className="mb-3">
        <div className="h-2.5 bg-krait-surface2 rounded animate-shimmer w-16 mb-2" />
        <SkeletonRows count={4} />
      </div>
      <div>
        <div className="h-2.5 bg-krait-surface2 rounded animate-shimmer w-16 mb-2" />
        <div className="grid grid-cols-2 gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-krait-surface1 rounded-lg p-3">
              <div className="w-4 h-4 rounded bg-krait-surface2 animate-shimmer mx-auto mb-2" />
              <div className="h-2.5 w-1/2 rounded bg-krait-surface2 animate-shimmer mx-auto mb-1.5" />
              <div className="h-2 w-3/4 rounded bg-krait-surface2 animate-shimmer mx-auto" />
            </div>
          ))}
        </div>
        <div className="mt-2">
          <SkeletonRows count={1} />
        </div>
      </div>
    </div>
  );
}

function SkeletonRows({ count }: { count: number }) {
  return (
    <div className="space-y-1.5">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-1.5 py-1">
          <div className="w-3.5 h-3.5 rounded bg-krait-surface2 animate-shimmer shrink-0" />
          <div className="h-2.5 w-16 rounded bg-krait-surface2 animate-shimmer shrink-0" />
          <div className="h-2.5 flex-1 rounded bg-krait-surface2 animate-shimmer" />
        </div>
      ))}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] uppercase tracking-wider text-text-tertiary font-medium mb-1.5">
      {children}
    </p>
  );
}

type Tone = 'default' | 'danger';

/**
 * One labelled value.
 *
 * The pending form names the stage that will produce the value rather than
 * showing a dash or a zero, because "not yet" and "measured, and it is nothing"
 * are different answers and this row is where that difference is visible.
 */
function Row({
  icon: Icon,
  label,
  value,
  pendingText,
  tone = 'default',
}: {
  icon: typeof Files;
  label: string;
  value: string | null;
  pendingText: string;
  tone?: Tone;
}) {
  return (
    <div className="flex items-center gap-3 px-1.5 py-1 rounded-lg text-[11px]">
      <Icon className="w-3.5 h-3.5 text-text-tertiary shrink-0" />
      <span className="text-text-tertiary w-20 shrink-0">{label}</span>
      {value ? (
        <span
          className={cn(
            'font-medium truncate',
            tone === 'danger' ? 'text-red-400' : 'text-foreground',
          )}
        >
          {value}
        </span>
      ) : (
        <span className="text-text-tertiary italic truncate">{pendingText}</span>
      )}
    </div>
  );
}

/**
 * A counted figure in the grid.
 *
 * Renders a shimmering block the same height the number would occupy, so the
 * grid does not reflow when the value arrives and an unmeasured count is never
 * mistakable for a measured zero.
 */
function Fact({
  icon: Icon,
  iconClass,
  label,
  fact,
}: {
  icon: typeof Files;
  iconClass: string;
  label: string;
  fact: RunFact<number>;
}) {
  return (
    <div className="bg-krait-surface1 rounded-lg p-3 text-center">
      <Icon className={cn('w-4 h-4 mx-auto mb-1', iconClass)} />
      {fact.state === 'pending' ? (
        <div
          className="h-7 my-0.5 rounded bg-krait-surface2 animate-shimmer w-2/3 mx-auto"
          role="status"
          aria-label={`${label} not measured yet`}
        />
      ) : (
        <p
          className="text-lg font-semibold text-foreground tabular-nums"
          title={
            fact.settled
              ? `${label}, measured`
              : `${label}, still being recounted`
          }
        >
          {fact.value.toLocaleString()}
        </p>
      )}
      <p className="text-[10px] text-text-tertiary uppercase tracking-wider">{label}</p>
    </div>
  );
}

/**
 * How long the run has taken, counting while it is still going.
 *
 * Three cases, because a run has three endings. Still going: the counter is
 * live, ticking once a second. Ended: the figure is the recorded distance from
 * start to the end timestamp, so it is the run's real duration and stops
 * moving. No start time yet: nothing to measure from, and it says so.
 *
 * The ended case uses the end timestamp rather than `now` deliberately. A
 * finished job left open on screen would otherwise report a duration that keeps
 * growing, and a failed one would tick forever -- both claiming the run is still
 * taking time to finish when it finished hours ago.
 */
function ElapsedRow({ job }: { job: AnalysisJob }) {
  const startedAt = usableTimestamp(job.started_at);
  const endedAt = usableTimestamp(job.completed_at);
  const finished = job.status === JobStatus.COMPLETED || job.status === JobStatus.FAILED;

  const [live, setLive] = useState(() => elapsedSince(startedAt));

  useEffect(() => {
    setLive(elapsedSince(startedAt));
    if (finished || !startedAt) return;

    const timer = setInterval(() => setLive(elapsedSince(startedAt)), 1000);
    return () => clearInterval(timer);
  }, [startedAt, finished]);

  const recorded = startedAt && endedAt ? elapsedBetween(startedAt, endedAt) : null;

  let shown: string;
  if (finished && recorded !== null) {
    shown = formatElapsed(Math.max(0, recorded));
  } else if (!startedAt) {
    shown = 'Once the run starts';
  } else {
    shown = live === null ? 'Measuring' : formatElapsed(live);
  }

  return (
    <div className="flex items-center gap-3 px-1.5 py-1 rounded-lg text-[11px]">
      <Clock className="w-3.5 h-3.5 text-text-tertiary shrink-0" />
      <span className="text-text-tertiary w-20 shrink-0">Elapsed</span>
      {startedAt ? (
        <span className="font-medium text-foreground tabular-nums">{shown}</span>
      ) : (
        <span className="text-text-tertiary italic truncate">{shown}</span>
      )}
    </div>
  );
}

/**
 * A timestamp this panel can use, or null.
 *
 * Null covers three cases that mean the same thing here: no value, an empty
 * string, and a string that is not a date. The third matters -- `formatDate`
 * ends in `Intl.DateTimeFormat.format`, which throws `RangeError` on an invalid
 * `Date`, so an unparseable timestamp would take the whole panel down rather
 * than render one bad row. Guarding it here means every consumer below can treat
 * null as "not recorded".
 */
function usableTimestamp(value: string | null | undefined): string | null {
  if (!value) return null;
  return Number.isNaN(Date.parse(value)) ? null : value;
}

/** Seconds since `startedAt`, or null when the clock cannot be trusted. */
function elapsedSince(startedAt: string | null): number | null {
  if (!startedAt) return null;
  const start = Date.parse(startedAt);
  if (Number.isNaN(start)) return null;
  const seconds = Math.floor((Date.now() - start) / 1000);
  // Negative means the browser's clock is behind the service's. Guessing there
  // would put an absurd elapsed time on screen.
  return seconds < 0 ? null : seconds;
}

/** Seconds from one recorded timestamp to another, or null if either is unusable. */
function elapsedBetween(from: string, to: string): number | null {
  const a = Date.parse(from);
  const b = Date.parse(to);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.floor((b - a) / 1000);
}

/**
 * `owner/repo` from a clone URL, or the host and path when it is not GitHub.
 *
 * A self-hosted or local URL still identifies the repository, so it is shown
 * rather than discarded -- just without pretending to be a GitHub path. The
 * scheme and any trailing `.git` go either way, since neither carries
 * information the panel needs.
 */
function formatRepo(url: string | null | undefined): string | null {
  if (!url) return null;
  const bare = url.replace(/^https?:\/\//, '').replace(/\.git$/, '');
  return bare.replace(/^github\.com\//, '');
}

export function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}
