'use client';

import Link from 'next/link';
import { GitBranch, BookOpen, AlertCircle } from 'lucide-react';
import type { Project } from '@/types/domain/projects';
import { cn } from '@/lib/utils';

const STATUS_BADGE: Record<string, { text: string; className: string }> = {
  planning:  { text: 'Planning',  className: 'text-[var(--text-secondary)] bg-[var(--krait-surface-3)] border-[var(--krait-border)]' },
  active:    { text: 'Active',    className: 'text-[var(--venom-yellow)] bg-[var(--venom-glow)] border-[var(--venom-gold)]/30' },
  completed: { text: 'Completed', className: 'text-[var(--color-success)] bg-[var(--color-success)]/10 border-[var(--color-success)]/20' },
  archived:  { text: 'Archived',  className: 'text-[var(--text-tertiary)] bg-[var(--krait-surface-2)] border-[var(--krait-border)]' },
};

interface ProjectCardProps {
  project: Project;
  workspaceSlug: string;
}

export function ProjectCard({ project, workspaceSlug }: ProjectCardProps) {
  const badge = STATUS_BADGE[project.status];
  const progress =
    project.task_count > 0
      ? Math.round((project.done_task_count / project.task_count) * 100)
      : 0;

  return (
    <Link
      href={`/${workspaceSlug}/projects/${project.id}`}
      className={cn(
        'group block',
        'bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[8px]',
        'p-5',
        'hover:border-[var(--krait-border-hi)]',
        'hover:shadow-[var(--shadow-venom)]',
        'transition-all duration-150',
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="w-9 h-9 rounded-[6px] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] flex items-center justify-center text-[18px] shrink-0">
          {project.icon || '\uD83D\uDCCB'}
        </div>
        <span
          className={cn(
            'text-[11px] font-medium px-2 py-0.5 rounded border',
            badge.className,
          )}
        >
          {badge.text}
        </span>
      </div>

      <h3 className="text-[14px] font-medium text-[var(--text-primary)] mb-0.5 group-hover:text-[var(--venom-yellow)] transition-colors line-clamp-1">
        {project.name}
      </h3>
      {project.description && (
        <p className="text-[12px] text-[var(--text-secondary)] mb-4 line-clamp-2 leading-relaxed">
          {project.description}
        </p>
      )}

      <div className="flex items-center gap-4 text-[12px] text-[var(--text-secondary)] mb-4">
        <span>{project.task_count} tasks</span>
        {project.blocked_task_count > 0 && (
          <span className="flex items-center gap-1 text-[var(--color-error)]">
            <AlertCircle size={11} />
            {project.blocked_task_count} blocked
          </span>
        )}
        {project.repository && (
          <span className="flex items-center gap-1 text-[var(--text-tertiary)]">
            <GitBranch size={11} />
            {project.repository.github_repo.split('/')[1]}
          </span>
        )}
        {project.knowledge_space && (
          <span className="flex items-center gap-1 text-[var(--text-tertiary)]">
            <BookOpen size={11} />
          </span>
        )}
      </div>

      {project.task_count > 0 && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px] text-[var(--text-tertiary)]">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1 w-full bg-[var(--krait-surface-3)] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${progress}%`,
                background: 'linear-gradient(90deg, var(--venom-gold), var(--venom-yellow))',
              }}
            />
          </div>
        </div>
      )}
    </Link>
  );
}
