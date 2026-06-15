'use client';

import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { useCreateTask, useProjects } from '@/lib/hooks/use-projects';
import type { TaskCreatePayload, TaskPriority, TaskType } from '@/types/domain/projects';
import { cn } from '@/lib/utils';

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

  const { data: projects } = useProjects(workspaceId);
  const createTask = useCreateTask(workspaceId);

  const handleSubmit = async () => {
    if (!title.trim() || !projectId) return;
    const payload: TaskCreatePayload = {
      title: title.trim(),
      project_id: projectId,
      priority,
      task_type: taskType,
    };
    await createTask.mutateAsync(payload);
    setTitle('');
    onClose();
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
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) handleSubmit();
            if (e.key === 'Escape') onClose();
          }}
          placeholder="Issue title"
          className="w-full bg-transparent text-[15px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none mb-4"
        />

        <div className="flex items-center gap-2 flex-wrap mb-5">
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="text-[12px] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[5px] px-2 py-1 outline-none focus:border-[var(--krait-border-hi)]"
          >
            <option value="">Select project...</option>
            {(projects ?? []).map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>

          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
            className="text-[12px] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[5px] px-2 py-1 outline-none focus:border-[var(--krait-border-hi)]"
          >
            {(['critical', 'high', 'medium', 'low'] as const).map((p) => (
              <option key={p} value={p} className="capitalize">{p}</option>
            ))}
          </select>

          <select
            value={taskType}
            onChange={(e) => setTaskType(e.target.value as TaskType)}
            className="text-[12px] bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[5px] px-2 py-1 outline-none focus:border-[var(--krait-border-hi)]"
          >
            {(['feature', 'bug', 'improvement', 'research', 'spike', 'documentation', 'technical_debt', 'incident'] as const).map((t) => (
              <option key={t} value={t}>{t.replace('_', ' ')}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center justify-between border-t border-[var(--krait-border)] pt-3">
          <span className="text-[11px] text-[var(--text-tertiary)]">
            Press Enter to create - Esc to cancel
          </span>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !projectId || createTask.isPending}
            className={cn(
              'flex items-center gap-2 text-[12px] font-medium px-3.5 py-1.5 rounded-[6px] text-black transition-opacity',
              (!title.trim() || !projectId) && 'opacity-40 cursor-not-allowed',
            )}
            style={{ background: 'var(--venom-yellow)' }}
          >
            {createTask.isPending && <Loader2 size={12} className="animate-spin" />}
            Create Issue
          </button>
        </div>
      </div>
    </div>
  );
}
