'use client';

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GitBranch, BookOpen } from 'lucide-react';
import type { Task } from '@/types/domain/projects';
import { PriorityIcon } from './priority-icon';
import { useProjectsStore } from '@/lib/stores/projects-store';
import { cn } from '@/lib/utils';

const PRIORITY_BORDER: Record<string, string> = {
  critical: 'border-l-[var(--venom-orange)]',
  high: 'border-l-[var(--venom-yellow)]',
  medium: 'border-l-[var(--krait-border)]',
  low: 'border-l-transparent',
};

interface KanbanTaskCardProps {
  task: Task;
  isDragging?: boolean;
}

export function KanbanTaskCard({ task, isDragging = false }: KanbanTaskCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: task.id });

  const openTaskDrawer = useProjectsStore(s => s.openTaskDrawer);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={cn(
        'group relative',
        'bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[6px]',
        'border-l-2 p-3',
        PRIORITY_BORDER[task.priority],
        'cursor-grab active:cursor-grabbing',
        'hover:border-[var(--krait-border-hi)] transition-colors duration-100',
        isDragging && 'opacity-50 shadow-xl shadow-black/40'
      )}
      onClick={e => {
        if (!isDragging) {
          e.stopPropagation();
          openTaskDrawer(task.id);
        }
      }}
    >
      <div className="flex items-start gap-2 mb-2">
        <PriorityIcon priority={task.priority} size={12} />
        <span className="text-[13px] text-[var(--text-primary)] leading-snug group-hover:text-[var(--venom-yellow)] transition-colors line-clamp-2">
          {task.title}
        </span>
      </div>

      <div className="flex items-center gap-2 mt-2">
        {task.repository_links[0] && (
          <span className="flex items-center gap-1 text-[11px] text-[var(--text-tertiary)] bg-[var(--krait-surface-3)] px-1.5 py-0.5 rounded truncate max-w-[80px]">
            <GitBranch size={10} />
            {task.repository_links[0].repository_github_repo.split('/')[1]}
          </span>
        )}

        {task.knowledge_links[0] && (
          <span className="flex items-center gap-1 text-[11px] text-[var(--text-tertiary)] bg-[var(--krait-surface-3)] px-1.5 py-0.5 rounded truncate max-w-[80px]">
            <BookOpen size={10} />
            {task.knowledge_links[0].space_name}
          </span>
        )}

        {task.estimate_points != null && (
          <span className="ml-auto text-[11px] text-[var(--text-tertiary)] border border-[var(--krait-border)] px-1 py-0.5 rounded">
            {task.estimate_points}
          </span>
        )}

        <div className="w-4 h-4 rounded-full bg-[var(--krait-surface-4)] border border-[var(--krait-border)] flex items-center justify-center text-[8px] text-[var(--text-secondary)] shrink-0">
          {task.assignee_id ? task.assignee_id.slice(0, 2).toUpperCase() : '+'}
        </div>
      </div>
    </div>
  );
}
