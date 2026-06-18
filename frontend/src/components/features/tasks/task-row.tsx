'use client';

import type { Task } from '@/types/domain/projects';
import { PriorityIcon } from './priority-icon';
import { StatusIcon } from './status-icon';
import { useProjectsStore } from '@/lib/stores/projects-store';
import { cn } from '@/lib/utils';

const PRIORITY_BORDER: Record<string, string> = {
  critical: 'border-l-[var(--venom-orange)]',
  high:     'border-l-[var(--venom-yellow)]',
  medium:   'border-l-[var(--krait-border)]',
  low:      'border-l-transparent',
};

interface TaskRowProps {
  task: Task;
  identifier?: string;
}

export function TaskRow({ task, identifier }: TaskRowProps) {
  const openTaskDrawer = useProjectsStore((s) => s.openTaskDrawer);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => openTaskDrawer(task.id)}
      onKeyDown={(e) => e.key === 'Enter' && openTaskDrawer(task.id)}
      className={cn(
        'group flex items-center gap-3 px-4 py-2',
        'border-l-2',
        PRIORITY_BORDER[task.priority],
        'hover:bg-[var(--krait-surface-2)] transition-colors duration-100',
        'cursor-pointer text-[13px]',
      )}
    >
      <StatusIcon status={task.status} size={14} />

      {identifier && (
        <span className="font-mono text-[11px] text-[var(--text-tertiary)] w-14 shrink-0">
          {identifier}
        </span>
      )}

      <PriorityIcon priority={task.priority} size={13} />

      <span className="flex-1 text-[var(--text-primary)] group-hover:text-[var(--venom-yellow)] transition-colors truncate">
        {task.title}
      </span>

      <div className="flex items-center gap-2 shrink-0">
        {task.repository_links[0] && (
          <span className="hidden sm:inline-block text-[11px] text-[var(--text-tertiary)] bg-[var(--krait-surface-3)] px-1.5 py-0.5 rounded truncate max-w-[100px]">
            {task.repository_links[0].repository_github_repo.split('/')[1]}
          </span>
        )}

        {task.estimate_points != null && (
          <span className="hidden md:inline-block text-[11px] text-[var(--text-tertiary)] border border-[var(--krait-border)] px-1.5 py-0.5 rounded">
            {task.estimate_points}pt
          </span>
        )}

        {task.due_date && (
          <span className={cn(
            'text-[11px] px-1.5 py-0.5 rounded border',
            new Date(task.due_date) < new Date()
              ? 'text-[var(--color-error)] border-[var(--color-error)]/30 bg-[var(--color-error)]/10'
              : 'text-[var(--text-secondary)] border-[var(--krait-border)] bg-[var(--krait-surface-2)]',
          )}>
            {new Date(task.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </span>
        )}

        <div className="w-5 h-5 rounded-full shrink-0 bg-[var(--krait-surface-4)] border border-[var(--krait-border)] flex items-center justify-center text-[9px] text-[var(--text-secondary)]">
          {task.assignee_id ? task.assignee_id.slice(0, 2).toUpperCase() : (
            <span className="text-[var(--text-tertiary)]">+</span>
          )}
        </div>
      </div>
    </div>
  );
}
