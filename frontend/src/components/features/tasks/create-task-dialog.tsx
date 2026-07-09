'use client';

import { useState } from 'react';
import { X, Loader2, Link2, Plus, CalendarDays } from 'lucide-react';
import { useCreateTask, useProjects, useTasks } from '@/lib/hooks/use-projects';
import { taskEndpoints } from '@/lib/api/endpoints/projects';
import type {
  TaskCreatePayload,
  TaskPriority,
  TaskType,
  TaskStatus,
  TaskLinkType,
} from '@/types/domain/projects';
import { cn } from '@/lib/utils';

const STATUS_ORDER: TaskStatus[] = [
  'backlog',
  'todo',
  'in_progress',
  'in_review',
  'blocked',
  'done',
  'cancelled',
];

const LINK_TYPES: { value: TaskLinkType; label: string }[] = [
  { value: 'blocks', label: 'Blocks' },
  { value: 'blocked_by', label: 'Blocked by' },
  { value: 'duplicates', label: 'Duplicates' },
  { value: 'relates_to', label: 'Relates to' },
  { value: 'caused_by', label: 'Caused by' },
];

interface PendingDep {
  taskId: string;
  taskTitle: string;
  type: TaskLinkType;
}

interface CreateTaskDialogProps {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  defaultProjectId?: string;
}

export function CreateTaskDialog({
  open,
  onClose,
  workspaceId,
  defaultProjectId,
}: CreateTaskDialogProps) {
  const [title, setTitle] = useState('');
  const [projectId, setProjectId] = useState(defaultProjectId ?? '');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [taskType, setTaskType] = useState<TaskType>('feature');
  const [status, setStatus] = useState<TaskStatus>('backlog');
  const [dueDate, setDueDate] = useState('');
  const [dueDateEditing, setDueDateEditing] = useState(false);

  const [depsOpen, setDepsOpen] = useState(false);
  const [depTaskId, setDepTaskId] = useState('');
  const [depType, setDepType] = useState<TaskLinkType>('relates_to');
  const [pendingDeps, setPendingDeps] = useState<PendingDep[]>([]);
  const [addingDeps, setAddingDeps] = useState(false);

  const { data: projects } = useProjects(workspaceId);
  const { data: allTasks } = useTasks(workspaceId);
  const createTask = useCreateTask(workspaceId);

  const clearForm = () => {
    setTitle('');
    setProjectId(defaultProjectId ?? '');
    setPriority('medium');
    setTaskType('feature');
    setStatus('backlog');
    setDueDate('');
    setDepsOpen(false);
    setDepTaskId('');
    setDepType('relates_to');
    setPendingDeps([]);
    setAddingDeps(false);
  };

  const handleSubmit = async () => {
    if (!title.trim() || !projectId) return;
    const payload: TaskCreatePayload = {
      title: title.trim(),
      project_id: projectId,
      priority,
      task_type: taskType,
      status,
      due_date: dueDate || null,
    };

    const createdTask = await createTask.mutateAsync(payload);

    if (pendingDeps.length > 0 && createdTask?.id) {
      setAddingDeps(true);
      try {
        await Promise.all(
          pendingDeps.map(dep =>
            taskEndpoints.addDependency(workspaceId, createdTask.id, {
              target_task_id: dep.taskId,
              relationship_type: dep.type,
            })
          )
        );
      } catch {
        // dependencies failed but task was created — still close
      }
    }

    clearForm();
    onClose();
  };

  const addPendingDep = () => {
    if (!depTaskId) return;
    const task = (allTasks?.results ?? []).find(t => t.id === depTaskId);
    if (!task) return;
    if (pendingDeps.some(d => d.taskId === depTaskId)) return;
    setPendingDeps(prev => [
      ...prev,
      { taskId: depTaskId, taskTitle: task.title, type: depType },
    ]);
    setDepTaskId('');
    setDepsOpen(false);
  };

  const removePendingDep = (taskId: string) => {
    setPendingDeps(prev => prev.filter(d => d.taskId !== taskId));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !depsOpen) {
      handleSubmit();
    }
    if (e.key === 'Escape') onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative w-full max-w-lg bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[10px] p-5 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[14px] font-medium text-[var(--text-primary)]">New Issue</h2>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-[var(--text-tertiary)] border border-[var(--krait-border)] px-1.5 py-0.5 rounded">
              Esc
            </span>
            <button
              onClick={onClose}
              className="p-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--krait-surface-3)] transition-colors"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        <input
          autoFocus
          value={title}
          onChange={e => setTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Issue title"
          className="w-full bg-transparent text-[15px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none mb-4"
        />

        <div className="flex items-center gap-2 flex-wrap mb-4">
          <select
            value={projectId}
            onChange={e => setProjectId(e.target.value)}
            className="text-[12px] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[5px] px-2 py-1 outline-none focus:border-[var(--krait-border-hi)]"
          >
            <option value="">Select project...</option>
            {(projects ?? []).map(p => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={e => setStatus(e.target.value as TaskStatus)}
            className="text-[12px] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[5px] px-2 py-1 outline-none focus:border-[var(--krait-border-hi)]"
          >
            {STATUS_ORDER.map(s => (
              <option key={s} value={s}>
                {s.replace('_', ' ')}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1">
            {(['critical', 'high', 'medium', 'low'] as const).map(p => (
              <button
                key={p}
                type="button"
                onClick={() => setPriority(p)}
                className={cn(
                  'text-[11px] font-medium px-2 py-1 rounded-[5px] capitalize transition-all',
                  priority === p
                    ? 'text-black'
                    : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] bg-[var(--krait-surface-2)] border border-[var(--krait-border)]'
                )}
                style={
                  priority === p
                    ? {
                        background:
                          p === 'critical'
                            ? '#ef4444'
                            : p === 'high'
                              ? '#f97316'
                              : p === 'medium'
                                ? '#eab308'
                                : '#22c55e',
                        borderColor:
                          p === 'critical'
                            ? '#ef4444'
                            : p === 'high'
                              ? '#f97316'
                              : p === 'medium'
                                ? '#eab308'
                                : '#22c55e',
                      }
                    : undefined
                }
              >
                {p}
              </button>
            ))}
          </div>

          <select
            value={taskType}
            onChange={e => setTaskType(e.target.value as TaskType)}
            className="text-[12px] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[5px] px-2 py-1 outline-none focus:border-[var(--krait-border-hi)]"
          >
            {(
              [
                'feature',
                'bug',
                'improvement',
                'research',
                'spike',
                'documentation',
                'technical_debt',
                'incident',
              ] as const
            ).map(t => (
              <option key={t} value={t}>
                {t.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 mb-4">
          <CalendarDays size={13} className="text-[var(--text-tertiary)]" />
          {dueDateEditing ? (
            <input
              autoFocus
              type="date"
              value={dueDate}
              onChange={e => setDueDate(e.target.value)}
              onBlur={() => setDueDateEditing(false)}
              onKeyDown={e => {
                if (e.key === 'Escape') setDueDateEditing(false);
              }}
              className="text-[12px] bg-[var(--krait-surface-2)] border border-[var(--krait-border-hi)] text-[var(--text-primary)] rounded-[5px] px-2 py-1 outline-none [color-scheme:dark]"
            />
          ) : (
            <button
              type="button"
              onClick={() => setDueDateEditing(true)}
              className="text-[12px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] rounded-[5px] px-2.5 py-1 transition-colors"
            >
              {dueDate
                ? new Date(dueDate).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })
                : 'No due date'}
            </button>
          )}
          {dueDate && !dueDateEditing && (
            <button
              type="button"
              onClick={() => setDueDate('')}
              className="p-0.5 rounded text-[var(--text-tertiary)] hover:text-[var(--color-error)] transition-colors"
              title="Clear due date"
            >
              <X size={12} />
            </button>
          )}
        </div>

        <div className="border-t border-[var(--krait-border)] pt-3 mb-4">
          <button
            onClick={() => setDepsOpen(!depsOpen)}
            className="flex items-center gap-1.5 text-[12px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <Link2 size={13} />
            Dependencies
            <Plus size={12} className="ml-1" />
          </button>

          {pendingDeps.length > 0 && (
            <div className="mt-2 space-y-1">
              {pendingDeps.map(dep => (
                <div
                  key={dep.taskId}
                  className="flex items-center gap-2 py-1.5 px-2 rounded bg-[var(--krait-surface-2)] text-[12px] group"
                >
                  <span className="text-[var(--text-tertiary)] capitalize shrink-0 text-[11px]">
                    {dep.type.replace('_', ' ')}
                  </span>
                  <span className="text-[var(--text-secondary)] flex-1 truncate">
                    {dep.taskTitle}
                  </span>
                  <button
                    onClick={() => removePendingDep(dep.taskId)}
                    disabled={addingDeps}
                    className="p-0.5 rounded text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 hover:text-[var(--color-error)] transition-all disabled:opacity-30"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {depsOpen && (
            <div className="mt-2 space-y-2 p-2 bg-[var(--krait-surface-2)] rounded-[6px]">
              <select
                autoFocus
                value={depTaskId}
                onChange={e => setDepTaskId(e.target.value)}
                className="w-full bg-[var(--krait-surface-1)] border border-[var(--krait-border)] text-[12px] text-[var(--text-primary)] rounded-[4px] px-2 py-1.5 outline-none"
              >
                <option value="">Select task...</option>
                {(allTasks?.results ?? []).map(t => (
                  <option key={t.id} value={t.id}>
                    {t.title}
                  </option>
                ))}
              </select>
              <select
                value={depType}
                onChange={e => setDepType(e.target.value as TaskLinkType)}
                className="w-full bg-[var(--krait-surface-1)] border border-[var(--krait-border)] text-[12px] text-[var(--text-primary)] rounded-[4px] px-2 py-1.5 outline-none"
              >
                {LINK_TYPES.map(lt => (
                  <option key={lt.value} value={lt.value}>
                    {lt.label}
                  </option>
                ))}
              </select>
              <div className="flex items-center justify-end gap-2">
                <button
                  onClick={() => setDepsOpen(false)}
                  className="text-[11px] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={addPendingDep}
                  disabled={!depTaskId}
                  className="flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 rounded-[4px] text-black transition-opacity disabled:opacity-40"
                  style={{ background: 'var(--venom-yellow)' }}
                >
                  Add
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[var(--krait-border)] pt-3">
          <span className="text-[11px] text-[var(--text-tertiary)]">
            Press Enter to create - Esc to cancel
          </span>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !projectId || createTask.isPending || addingDeps}
            className={cn(
              'flex items-center gap-2 text-[12px] font-medium px-3.5 py-1.5 rounded-[6px] text-black transition-opacity',
              (!title.trim() || !projectId || createTask.isPending || addingDeps) &&
                'opacity-40 cursor-not-allowed'
            )}
            style={{ background: 'var(--venom-yellow)' }}
          >
            {(createTask.isPending || addingDeps) && (
              <Loader2 size={12} className="animate-spin" />
            )}
            {addingDeps ? 'Linking...' : 'Create Issue'}
          </button>
        </div>
      </div>
    </div>
  );
}
