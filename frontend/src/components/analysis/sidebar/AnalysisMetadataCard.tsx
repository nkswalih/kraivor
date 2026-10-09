'use client';

import {
  Files,
  Code2,
  Braces,
  FunctionSquare,
  Route,
  Languages,
  Clock,
  Calendar,
  GitBranch,
  Globe,
  Building2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import type { AnalysisMetadata as Metadata } from '@/types/domain/analysis';

interface MetaRow {
  icon: LucideIcon;
  label: string;
  value: string | number | null;
}

interface MetaSection {
  title: string;
  rows: MetaRow[];
}

export function AnalysisMetadataCard({
  data,
  isLoading,
  workspaceName,
  className,
}: {
  data: Metadata;
  isLoading?: boolean;
  /**
   * The workspace's human name, supplied by the caller because the job payload
   * only carries `workspace_id`.
   *
   * No id fallback: an id prefix is not a name anyone knows the workspace by,
   * so an unhydrated store leaves the row as an em-dash -- the same answer any
   * other unknown here gets -- instead of reprinting the identifier.
   */
  workspaceName?: string | null;
  className?: string;
}) {
  // A count that has not been measured renders as an em-dash, not as 0. Every
  // row below is nullable, and `row.value ?? '—'` is what draws the em-dash.
  const count = (value: number | null) => (value === null ? null : value.toLocaleString());

  const workspaceValue = workspaceName ?? null;

  // Grouped rather than a flat run of twelve: what the run was built from, what
  // it measured, and when it happened. The flat list answered all three in the
  // same undifferentiated column, which is why the card read as a dump.
  const sections: MetaSection[] = [
    {
      title: 'Source',
      rows: [
        {
          icon: Globe,
          label: 'Repository',
          value: data.repoUrl ? data.repoUrl.replace('https://github.com/', '') : null,
        },
        { icon: GitBranch, label: 'Branch', value: data.branch },
        { icon: Building2, label: 'Workspace', value: workspaceValue },
        {
          icon: Languages,
          label: 'Languages',
          value: data.languages === null ? null : data.languages.join(', ') || '—',
        },
      ],
    },
    {
      title: 'Code',
      rows: [
        { icon: Files, label: 'Files', value: count(data.totalFiles) },
        { icon: Code2, label: 'LOC', value: count(data.totalLines) },
        { icon: Braces, label: 'Classes', value: count(data.classes) },
        { icon: FunctionSquare, label: 'Functions', value: count(data.functions) },
        { icon: Route, label: 'Endpoints', value: count(data.endpoints) },
      ],
    },
    {
      title: 'Run',
      rows: [
        { icon: Clock, label: 'Duration', value: data.duration },
        {
          icon: Calendar,
          label: 'Started',
          value: data.startedAt ? formatRelativeTime(data.startedAt) : null,
        },
        {
          icon: Calendar,
          label: 'Completed',
          value: data.completedAt ? formatRelativeTime(data.completedAt) : null,
        },
      ],
    },
  ];

  if (isLoading) {
    return (
      <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
        <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-1/3 mb-3" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, sectionIndex) => (
            <div key={sectionIndex} className="space-y-2">
              <div className="h-2.5 w-12 bg-krait-surface2 rounded animate-shimmer" />
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <div className="w-5 h-5 bg-krait-surface2 rounded-md animate-shimmer shrink-0" />
                  <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-16" />
                  <div className="h-3 bg-krait-surface2 rounded animate-shimmer flex-1" />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <h3 className="text-[13px] font-semibold text-foreground mb-3">Analysis Metadata</h3>

      <div className="divide-y divide-border/70">
        {sections.map((section, index) => (
          <section
            key={section.title}
            className={cn(index > 0 && 'pt-3 mt-3')}
            aria-label={section.title}
          >
            <h4 className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary mb-1.5">
              {section.title}
            </h4>
            <div>
              {section.rows.map((row) => {
                const Icon = row.icon;
                const value = row.value ?? '—';
                return (
                  <div key={row.label} className="flex items-center gap-2.5 py-1">
                    <span className="grid h-5 w-5 shrink-0 place-items-center rounded-md border border-border/70 bg-krait-surface1">
                      <Icon className="w-3 h-3 text-text-tertiary" aria-hidden />
                    </span>
                    <span className="text-[11px] text-text-tertiary w-[72px] shrink-0">
                      {row.label}
                    </span>
                    {/* Left-aligned on purpose: right-aligning an overflowing
                        single line moves the clip to the start edge, which
                        suppresses the ellipsis, and `Languages` routinely
                        overflows a sidebar this narrow. */}
                    <span
                      className="flex-1 min-w-0 truncate text-[11px] font-medium text-foreground"
                      title={typeof row.value === 'string' ? row.value : undefined}
                    >
                      {value}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
