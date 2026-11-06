'use client';

import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Plus } from 'lucide-react';
import type { Task, TaskStatus } from '@/types/domain/projects';
import { KanbanTaskCard } from './kanban-task-card';
import { StatusIcon } from './status-icon';
import { useProjectsStore } from '@/lib/stores/projects-store';
import { cn } from '@/lib/utils';

const STATUS_LABELS: Record<TaskStatus, string> = {
  backlog: 'Backlog',
  todo: 'Todo',
  in_progress: 'In Progress',
  in_review: 'In Review',
  blocked: 'Blocked',
  done: 'Done',
  cancelled: 'Cancelled',
};

interface KanbanColumnProps {
  status: TaskStatus;
  tasks: Task[];
  projectId: string;
}

export function KanbanColumn({ status, tasks, projectId }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  const openCreateTask = useProjectsStore(s => s.openCreateTask);

  return (
    <div className="flex flex-col min-w-[260px] max-w-[260px]">
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <StatusIcon status={status} size={13} />
          <span className="text-[13px] font-medium text-[var(--text-primary)]">
            {STATUS_LABELS[status]}
          </span>
          <span className="text-[12px] text-[var(--text-tertiary)] ml-0.5">{tasks.length}</span>
        </div>
        <button
          onClick={() => openCreateTask(projectId)}
          className="p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--venom-yellow)] hover:bg-[var(--krait-surface-3)] transition-colors"
        >
          <Plus size={13} />
        </button>
      </div>

      <div
        ref={setNodeRef}
        className={cn(
          'flex-1 space-y-2 min-h-[120px] rounded-[6px] p-1 transition-colors duration-100',
          isOver && 'bg-[var(--venom-glow)] ring-1 ring-[var(--venom-yellow)]/20'
        )}
      >
        <SortableContext items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map(task => (
            <KanbanTaskCard key={task.id} task={task} />
          ))}
        </SortableContext>

        {tasks.length === 0 && (
          <div className="h-20 flex items-center justify-center">
            <span className="text-[12px] text-[var(--text-tertiary)]">Drop here</span>
          </div>
        )}
      </div>
    </div>
  );
}
