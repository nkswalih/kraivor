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
import { cn, formatRelativeTime, formatDate } from '@/lib/utils';
import type { AnalysisMetadata as Metadata } from '@/types/domain/analysis';

interface MetaRow {
  icon: typeof Files;
  label: string;
  value: string | number | null;
}

export function AnalysisMetadataCard({
  data,
  isLoading,
  className,
}: {
  data: Metadata;
  isLoading?: boolean;
  className?: string;
}) {
  const rows: MetaRow[] = [
    { icon: Files, label: 'Files', value: data.totalFiles.toLocaleString() },
    { icon: Code2, label: 'LOC', value: data.totalLines.toLocaleString() },
    { icon: Braces, label: 'Classes', value: data.classes.toLocaleString() },
    { icon: FunctionSquare, label: 'Functions', value: data.functions.toLocaleString() },
    { icon: Route, label: 'Endpoints', value: data.endpoints.toLocaleString() },
    { icon: Languages, label: 'Languages', value: data.languages.length > 0 ? data.languages.join(', ') : '—' },
    { icon: Clock, label: 'Duration', value: data.duration ?? '—' },
    { icon: Calendar, label: 'Started', value: data.startedAt ? formatRelativeTime(data.startedAt) : '—' },
    { icon: Calendar, label: 'Completed', value: data.completedAt ? formatRelativeTime(data.completedAt) : '—' },
    { icon: GitBranch, label: 'Branch', value: data.branch },
    { icon: Globe, label: 'Repository', value: data.repoUrl ? data.repoUrl.replace('https://github.com/', '') : '—' },
    { icon: Building2, label: 'Workspace', value: data.workspaceId ? data.workspaceId.slice(0, 8) : '—' },
  ];

  if (isLoading) {
    return (
      <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
        <div className="h-4 bg-krait-surface2 rounded animate-shimmer w-1/3 mb-3" />
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-4 h-4 bg-krait-surface2 rounded animate-shimmer" />
              <div className="h-3 bg-krait-surface2 rounded animate-shimmer w-16" />
              <div className="h-3 bg-krait-surface2 rounded animate-shimmer flex-1" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-card border border-border rounded-xl p-4', className)}>
      <h3 className="text-[13px] font-semibold text-foreground mb-3">Analysis Metadata</h3>
      <div className="space-y-1">
        {rows.map((row) => {
          const Icon = row.icon;
          return (
            <div
              key={row.label}
              className="flex items-center gap-3 px-1.5 py-1 rounded-lg text-[11px]"
            >
              <Icon className="w-3.5 h-3.5 text-text-tertiary shrink-0" />
              <span className="text-text-tertiary w-20 shrink-0">{row.label}</span>
              <span className="text-foreground font-medium truncate">
                {row.value ?? '—'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
