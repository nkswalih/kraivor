'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CheckSquare, Plus, Filter, Loader2, ChevronDown } from 'lucide-react';
import { useTasks } from '@/lib/hooks/use-projects';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useProjectsStore } from '@/lib/stores/projects-store';
import { TaskRow } from '@/components/features/tasks/task-row';
import { TaskDrawer } from '@/components/features/tasks/task-drawer';
import { CreateTaskDialog } from '@/components/features/tasks/create-task-dialog';
import { StatusIcon } from '@/components/features/tasks/status-icon';
import { KANBAN_COLUMNS, ACTIVE_TASK_STATUSES, type TaskStatus } from '@/types/domain/projects';
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

type View = 'active' | 'backlog';

export default function TasksPage() {
  const { workspace } = useParams<{ workspace: string }>();
  const workspaceId = useAuthStore(s => s.workspaceId) ?? workspace;
  const [activeView, setActiveView] = useState<View>('active');
  const [collapsedStatuses, setCollapsedStatuses] = useState<Set<TaskStatus>>(new Set());

  const { openCreateTask, createTaskOpen, createTaskDefaultProjectId, closeCreateTask } =
    useProjectsStore();

  const { data, isLoading } = useTasks(workspaceId);
  const tasks = data?.results ?? [];

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        e.key === 'c' &&
        !e.metaKey &&
        !e.ctrlKey &&
        !e.shiftKey &&
        document.activeElement?.tagName !== 'INPUT' &&
        document.activeElement?.tagName !== 'TEXTAREA'
      ) {
        openCreateTask();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [openCreateTask]);

  const statusesToShow: TaskStatus[] =
    activeView === 'active'
      ? KANBAN_COLUMNS.filter(s => ACTIVE_TASK_STATUSES.includes(s) || s === 'done')
      : ['backlog', 'cancelled'];

  const grouped = statusesToShow.reduce<Record<TaskStatus, typeof tasks>>(
    (acc, status) => {
      acc[status] = tasks.filter(t => t.status === status);
      return acc;
    },
    {} as Record<TaskStatus, typeof tasks>
  );

  const toggleCollapse = (status: TaskStatus) => {
    setCollapsedStatuses(prev => {
      const next = new Set(prev);
      next.has(status) ? next.delete(status) : next.add(status);
      return next;
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-[var(--krait-border)] shrink-0 bg-[var(--krait-obsidian)]">
        <div className="flex items-center gap-4">
          <h1 className="text-[15px] font-medium text-[var(--text-primary)] flex items-center gap-2">
            <CheckSquare size={17} className="text-[var(--venom-yellow)]" />
            Issues
          </h1>
          <div className="h-4 w-px bg-[var(--krait-border)]" />
          <div className="flex items-center gap-0.5">
            {(['active', 'backlog'] as const).map(view => (
              <button
                key={view}
                onClick={() => setActiveView(view)}
                className={cn(
                  'text-[12px] font-medium px-2.5 py-1 rounded-[4px] capitalize transition-colors',
                  activeView === view
                    ? 'bg-[var(--krait-surface-3)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                )}
              >
                {view}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="p-2 border border-[var(--krait-border)] bg-[var(--krait-surface-1)] rounded-[6px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
            <Filter size={14} />
          </button>

          <span className="hidden lg:inline text-[11px] text-[var(--text-tertiary)] border border-[var(--krait-border)] px-1.5 py-0.5 rounded">
            C
          </span>

          <button
            onClick={() => openCreateTask()}
            className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-black transition-opacity hover:opacity-90"
            style={{ background: 'var(--venom-yellow)' }}
          >
            <Plus size={13} />
            New Issue
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-[var(--krait-void)]">
        {isLoading && (
          <div className="flex items-center justify-center h-40">
            <Loader2 size={18} className="animate-spin text-[var(--venom-yellow)]" />
          </div>
        )}

        {!isLoading && (
          <div className="py-2">
            {statusesToShow.map(status => {
              const statusTasks = grouped[status] ?? [];
              const isCollapsed = collapsedStatuses.has(status);

              return (
                <div key={status} className="mb-2">
                  <button
                    onClick={() => toggleCollapse(status)}
                    className="flex items-center gap-2 w-full px-6 py-2 text-[12px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors group"
                  >
                    <StatusIcon status={status} size={13} />
                    <span>{STATUS_LABELS[status]}</span>
                    <span className="text-[var(--text-tertiary)]">{statusTasks.length}</span>
                    <ChevronDown
                      size={13}
                      className={cn(
                        'ml-auto transition-transform duration-150 text-[var(--text-tertiary)] group-hover:text-[var(--text-secondary)]',
                        isCollapsed && '-rotate-90'
                      )}
                    />
                  </button>

                  {!isCollapsed && (
                    <div className="border-t border-b border-[var(--krait-border)] bg-[var(--krait-surface-1)] divide-y divide-[var(--krait-border)]/50">
                      {statusTasks.length === 0 ? (
                        <div className="px-6 py-3 text-[12px] text-[var(--text-tertiary)]">
                          No issues
                        </div>
                      ) : (
                        statusTasks.map((task, i) => (
                          <TaskRow
                            key={task.id}
                            task={task}
                            identifier={`KRV-${String(i + 1).padStart(2, '0')}`}
                          />
                        ))
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {tasks.length === 0 && (
              <div className="flex flex-col items-center justify-center h-60 text-center">
                <CheckSquare size={32} className="text-[var(--text-tertiary)] mb-3" />
                <p className="text-[14px] text-[var(--text-secondary)]">No issues yet</p>
                <p className="text-[12px] text-[var(--text-tertiary)] mt-1">
                  Press <kbd className="border border-[var(--krait-border)] px-1 rounded">C</kbd> to
                  create your first issue.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      <TaskDrawer workspaceId={workspaceId} />
      <CreateTaskDialog
        open={createTaskOpen}
        onClose={closeCreateTask}
        workspaceId={workspaceId}
        defaultProjectId={createTaskDefaultProjectId}
      />
    </div>
  );
}
