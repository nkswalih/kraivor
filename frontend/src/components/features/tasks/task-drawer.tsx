'use client';

import { useState, useEffect, useRef } from 'react';
import { X, Link2, GitBranch, BookOpen, ChevronRight, Plus, Loader2, Trash2 } from 'lucide-react';
import { useProjectsStore } from '@/lib/stores/projects-store';
import {
  useTask,
  useUpdateTask,
  useTasks,
  useDeleteTask,
  useRepositoriesList,
  useKnowledgeSpacesList,
  useAddDependency,
  useRemoveDependency,
  useLinkRepository,
  useRemoveLinkRepository,
  useLinkKnowledge,
  useRemoveLinkKnowledge,
} from '@/lib/hooks/use-projects';
import { PriorityIcon } from './priority-icon';
import { StatusIcon } from './status-icon';
import { cn } from '@/lib/utils';
import type {
  TaskStatus,
  TaskPriority,
  TaskLinkType,
} from '@/types/domain/projects';

interface TaskDrawerProps {
  workspaceId: string;
}

const STATUS_ORDER: TaskStatus[] = [
  'backlog', 'todo', 'in_progress', 'in_review', 'blocked', 'done', 'cancelled',
];

const LINK_TYPES: { value: TaskLinkType; label: string }[] = [
  { value: 'blocks', label: 'Blocks' },
  { value: 'blocked_by', label: 'Blocked by' },
  { value: 'duplicates', label: 'Duplicates' },
  { value: 'relates_to', label: 'Relates to' },
  { value: 'caused_by', label: 'Caused by' },
];

export function TaskDrawer({ workspaceId }: TaskDrawerProps) {
  const { drawerOpen, drawerTaskId, closeTaskDrawer } = useProjectsStore();
  const { data: task, isLoading } = useTask(workspaceId, drawerTaskId ?? '');
  const updateTask = useUpdateTask(workspaceId, drawerTaskId ?? '');
  const addDependency = useAddDependency(workspaceId, drawerTaskId ?? '');
  const removeDependency = useRemoveDependency(workspaceId, drawerTaskId ?? '');
  const linkRepository = useLinkRepository(workspaceId, drawerTaskId ?? '');
  const removeLinkRepository = useRemoveLinkRepository(workspaceId, drawerTaskId ?? '');
  const linkKnowledge = useLinkKnowledge(workspaceId, drawerTaskId ?? '');
  const removeLinkKnowledge = useRemoveLinkKnowledge(workspaceId, drawerTaskId ?? '');
  const deleteTask = useDeleteTask(workspaceId);
  const { data: repos } = useRepositoriesList(workspaceId);
  const { data: knowledgeSpaces } = useKnowledgeSpacesList(workspaceId);
  const { data: allTasks } = useTasks(workspaceId);
  const [confirmDeleteTask, setConfirmDeleteTask] = useState(false);

  const drawerRef = useRef<HTMLDivElement>(null);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [addDepOpen, setAddDepOpen] = useState(false);
  const [addRepoOpen, setAddRepoOpen] = useState(false);
  const [addKnowOpen, setAddKnowOpen] = useState(false);
  const [depTaskId, setDepTaskId] = useState('');
  const [depType, setDepType] = useState<TaskLinkType>('relates_to');
  const [selectedRepoId, setSelectedRepoId] = useState('');
  const [selectedKnowId, setSelectedKnowId] = useState('');

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeTaskDrawer();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [closeTaskDrawer]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        closeTaskDrawer();
      }
    };
    if (drawerOpen) {
      setTimeout(() => document.addEventListener('mousedown', handler), 100);
    }
    return () => document.removeEventListener('mousedown', handler);
  }, [drawerOpen, closeTaskDrawer]);

  useEffect(() => {
    setEditingField(null);
    setAddDepOpen(false);
    setAddRepoOpen(false);
    setAddKnowOpen(false);
  }, [drawerTaskId]);

  const updateField = (field: string, value: unknown) => {
    updateTask.mutate({ [field]: value });
    setEditingField(null);
  };

  return (
    <>
      {drawerOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={closeTaskDrawer}
        />
      )}

      <div
        ref={drawerRef}
        style={{
          transition: 'transform 220ms cubic-bezier(0.16, 1, 0.3, 1), opacity 180ms ease',
          transform: drawerOpen ? 'translateX(0)' : 'translateX(100%)',
          opacity: drawerOpen ? 1 : 0,
        }}
        className={cn(
          'fixed right-0 top-0 bottom-0 z-40',
          'w-full max-w-[480px]',
          'bg-[var(--krait-surface-1)] border-l border-[var(--krait-border)]',
          'flex flex-col overflow-hidden',
        )}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--krait-border)] shrink-0">
          <div className="flex items-center gap-2 text-[12px] text-[var(--text-tertiary)]">
            {task && (
              <>
                <span className="font-mono">{task.project_id.slice(0, 8)}</span>
                <ChevronRight size={12} />
                <span>Task</span>
              </>
            )}
          </div>
          <button
            onClick={closeTaskDrawer}
            className="p-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--krait-surface-3)] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
          {isLoading && (
            <div className="space-y-3">
              <div className="h-6 w-3/4 bg-[var(--krait-surface-3)] rounded animate-pulse" />
              <div className="h-4 w-1/2 bg-[var(--krait-surface-2)] rounded animate-pulse" />
            </div>
          )}

          {task && (
            <>
              {/* Title & Description */}
              <div>
                <h2 className="text-[16px] font-medium text-[var(--text-primary)] leading-snug mb-1">
                  {task.title}
                </h2>
                {task.description && (
                  <p className="text-[13px] text-[var(--text-secondary)] leading-relaxed">
                    {task.description}
                  </p>
                )}
              </div>

              {/* Editable Fields */}
              <div className="grid grid-cols-2 gap-3">
                <MetaField label="Status">
                  {editingField === 'status' ? (
                    <select
                      autoFocus
                      value={task.status}
                      onChange={(e) => updateField('status', e.target.value)}
                      onBlur={() => setEditingField(null)}
                      onKeyDown={(e) => e.key === 'Escape' && setEditingField(null)}
                      className="w-full bg-[var(--krait-surface-3)] border border-[var(--krait-border-hi)] text-[13px] text-[var(--text-primary)] rounded-[4px] px-2 py-1 outline-none"
                    >
                      {STATUS_ORDER.map((s) => (
                        <option key={s} value={s}>{s.replace('_', ' ')}</option>
                      ))}
                    </select>
                  ) : (
                    <button
                      onClick={() => setEditingField('status')}
                      className="flex items-center gap-1.5 text-[13px] text-[var(--text-primary)] capitalize hover:bg-[var(--krait-surface-2)] rounded-[4px] -mx-1 px-1 py-0.5 transition-colors w-full text-left"
                    >
                      <StatusIcon status={task.status} size={12} />
                      {task.status.replace('_', ' ')}
                    </button>
                  )}
                </MetaField>

                <MetaField label="Priority">
                  {editingField === 'priority' ? (
                    <select
                      autoFocus
                      value={task.priority}
                      onChange={(e) => updateField('priority', e.target.value)}
                      onBlur={() => setEditingField(null)}
                      onKeyDown={(e) => e.key === 'Escape' && setEditingField(null)}
                      className="w-full bg-[var(--krait-surface-3)] border border-[var(--krait-border-hi)] text-[13px] text-[var(--text-primary)] rounded-[4px] px-2 py-1 outline-none"
                    >
                      {(['critical', 'high', 'medium', 'low'] as const).map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  ) : (
                    <button
                      onClick={() => setEditingField('priority')}
                      className="flex items-center gap-1.5 text-[13px] text-[var(--text-primary)] capitalize hover:bg-[var(--krait-surface-2)] rounded-[4px] -mx-1 px-1 py-0.5 transition-colors w-full text-left"
                    >
                      <PriorityIcon priority={task.priority} size={13} />
                      {task.priority}
                    </button>
                  )}
                </MetaField>

                <MetaField label="Due Date">
                  {editingField === 'due_date' ? (
                    <input
                      autoFocus
                      type="date"
                      value={task.due_date ?? ''}
                      onChange={(e) => updateField('due_date', e.target.value || null)}
                      onBlur={() => setEditingField(null)}
                      onKeyDown={(e) => e.key === 'Escape' && setEditingField(null)}
                      className="w-full bg-[var(--krait-surface-3)] border border-[var(--krait-border-hi)] text-[13px] text-[var(--text-primary)] rounded-[4px] px-2 py-1 outline-none"
                    />
                  ) : (
                    <button
                      onClick={() => setEditingField('due_date')}
                      className="text-[13px] text-[var(--text-primary)] hover:bg-[var(--krait-surface-2)] rounded-[4px] -mx-1 px-1 py-0.5 transition-colors w-full text-left"
                    >
                      {task.due_date
                        ? new Date(task.due_date).toLocaleDateString('en-US', {
                            month: 'short', day: 'numeric', year: 'numeric',
                          })
                        : '\u2014'}
                    </button>
                  )}
                </MetaField>

                <MetaField label="Points">
                  {editingField === 'estimate_points' ? (
                    <input
                      autoFocus
                      type="number"
                      min={0}
                      value={task.estimate_points ?? ''}
                      onChange={(e) => updateField('estimate_points', e.target.value ? Number(e.target.value) : null)}
                      onBlur={() => setEditingField(null)}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') setEditingField(null);
                        if (e.key === 'Enter') setEditingField(null);
                      }}
                      className="w-full bg-[var(--krait-surface-3)] border border-[var(--krait-border-hi)] text-[13px] text-[var(--text-primary)] rounded-[4px] px-2 py-1 outline-none"
                    />
                  ) : (
                    <button
                      onClick={() => setEditingField('estimate_points')}
                      className="text-[13px] text-[var(--text-primary)] hover:bg-[var(--krait-surface-2)] rounded-[4px] -mx-1 px-1 py-0.5 transition-colors w-full text-left"
                    >
                      {task.estimate_points ?? '\u2014'}
                    </button>
                  )}
                </MetaField>
              </div>

              {/* Dependencies */}
              <DrawerSection
                title="Dependencies"
                icon={<Link2 size={13} />}
                action={
                  <button
                    onClick={() => setAddDepOpen(!addDepOpen)}
                    className="p-0.5 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--krait-surface-3)] transition-colors"
                  >
                    <Plus size={14} />
                  </button>
                }
              >
                {task.dependencies.length > 0 && (
                  <div className="space-y-1 mb-2">
                    {task.dependencies.map((dep) => (
                      <div
                        key={dep.id}
                        className="flex items-center gap-2 py-1.5 px-2 rounded bg-[var(--krait-surface-2)] text-[12px] group"
                      >
                        <span className="text-[var(--text-tertiary)] capitalize shrink-0">
                          {dep.relationship_type.replace('_', ' ')}
                        </span>
                        <span className="text-[var(--text-secondary)] flex-1 truncate">
                          {dep.title}
                        </span>
                        <button
                          onClick={() => removeDependency.mutate(dep.id)}
                          className="p-0.5 rounded text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 hover:text-[var(--color-error)] transition-all"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {addDepOpen && (
                  <div className="space-y-2 p-2 bg-[var(--krait-surface-2)] rounded-[6px]">
                    <select
                      autoFocus
                      value={depTaskId}
                      onChange={(e) => setDepTaskId(e.target.value)}
                      className="w-full bg-[var(--krait-surface-1)] border border-[var(--krait-border)] text-[12px] text-[var(--text-primary)] rounded-[4px] px-2 py-1.5 outline-none"
                    >
                      <option value="">Select task...</option>
                      {(allTasks?.results ?? []).filter(t => t.id !== drawerTaskId).map((t) => (
                        <option key={t.id} value={t.id}>{t.title}</option>
                      ))}
                    </select>
                    <select
                      value={depType}
                      onChange={(e) => setDepType(e.target.value as TaskLinkType)}
                      className="w-full bg-[var(--krait-surface-1)] border border-[var(--krait-border)] text-[12px] text-[var(--text-primary)] rounded-[4px] px-2 py-1.5 outline-none"
                    >
                      {LINK_TYPES.map((lt) => (
                        <option key={lt.value} value={lt.value}>{lt.label}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => {
                        if (!depTaskId) return;
                        addDependency.mutate(
                          { target_task_id: depTaskId, relationship_type: depType },
                          { onSuccess: () => { setDepTaskId(''); setAddDepOpen(false); } },
                        );
                      }}
                      disabled={!depTaskId || addDependency.isPending}
                      className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-[4px] text-black transition-opacity disabled:opacity-40"
                      style={{ background: 'var(--venom-yellow)' }}
                    >
                      {addDependency.isPending && <Loader2 size={11} className="animate-spin" />}
                      Add
                    </button>
                  </div>
                )}
              </DrawerSection>

              {/* Repositories */}
              <DrawerSection
                title="Repositories"
                icon={<GitBranch size={13} />}
                action={
                  <button
                    onClick={() => setAddRepoOpen(!addRepoOpen)}
                    className="p-0.5 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--krait-surface-3)] transition-colors"
                  >
                    <Plus size={14} />
                  </button>
                }
              >
                {task.repository_links.length > 0 && (
                  <div className="space-y-1 mb-2">
                    {task.repository_links.map((link) => (
                      <div
                        key={link.id}
                        className="flex items-center gap-2 py-1.5 px-2 rounded bg-[var(--krait-surface-2)] text-[12px] group"
                      >
                        <GitBranch size={12} className="shrink-0 text-[var(--venom-yellow)]" />
                        <span className="text-[var(--text-secondary)] flex-1 truncate">
                          {link.repository_github_repo}
                        </span>
                        <button
                          onClick={() => removeLinkRepository.mutate(link.id)}
                          className="p-0.5 rounded text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 hover:text-[var(--color-error)] transition-all"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {addRepoOpen && (
                  <div className="space-y-2 p-2 bg-[var(--krait-surface-2)] rounded-[6px]">
                    <select
                      autoFocus
                      value={selectedRepoId}
                      onChange={(e) => setSelectedRepoId(e.target.value)}
                      className="w-full bg-[var(--krait-surface-1)] border border-[var(--krait-border)] text-[12px] text-[var(--text-primary)] rounded-[4px] px-2 py-1.5 outline-none"
                    >
                      <option value="">Select repository...</option>
                      {(repos ?? []).map((r) => (
                        <option key={r.id} value={r.id}>{r.github_repo}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => {
                        if (!selectedRepoId) return;
                        linkRepository.mutate(selectedRepoId, {
                          onSuccess: () => { setSelectedRepoId(''); setAddRepoOpen(false); },
                        });
                      }}
                      disabled={!selectedRepoId || linkRepository.isPending}
                      className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-[4px] text-black transition-opacity disabled:opacity-40"
                      style={{ background: 'var(--venom-yellow)' }}
                    >
                      {linkRepository.isPending && <Loader2 size={11} className="animate-spin" />}
                      Link
                    </button>
                  </div>
                )}
              </DrawerSection>

              {/* Knowledge Spaces */}
              <DrawerSection
                title="Knowledge"
                icon={<BookOpen size={13} />}
                action={
                  <button
                    onClick={() => setAddKnowOpen(!addKnowOpen)}
                    className="p-0.5 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--krait-surface-3)] transition-colors"
                  >
                    <Plus size={14} />
                  </button>
                }
              >
                {task.knowledge_links.length > 0 && (
                  <div className="space-y-1 mb-2">
                    {task.knowledge_links.map((link) => (
                      <div
                        key={link.id}
                        className="flex items-center gap-2 py-1.5 px-2 rounded bg-[var(--krait-surface-2)] text-[12px] group"
                      >
                        <BookOpen size={12} className="shrink-0 text-[var(--venom-yellow)]" />
                        <span className="text-[var(--text-secondary)] flex-1 truncate">
                          {link.space_name}
                        </span>
                        <button
                          onClick={() => removeLinkKnowledge.mutate(link.id)}
                          className="p-0.5 rounded text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 hover:text-[var(--color-error)] transition-all"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {addKnowOpen && (
                  <div className="space-y-2 p-2 bg-[var(--krait-surface-2)] rounded-[6px]">
                    <select
                      autoFocus
                      value={selectedKnowId}
                      onChange={(e) => setSelectedKnowId(e.target.value)}
                      className="w-full bg-[var(--krait-surface-1)] border border-[var(--krait-border)] text-[12px] text-[var(--text-primary)] rounded-[4px] px-2 py-1.5 outline-none"
                    >
                      <option value="">Select knowledge space...</option>
                      {(knowledgeSpaces ?? []).map((k) => (
                        <option key={k.id} value={k.id}>{k.name}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => {
                        if (!selectedKnowId) return;
                        linkKnowledge.mutate(selectedKnowId, {
                          onSuccess: () => { setSelectedKnowId(''); setAddKnowOpen(false); },
                        });
                      }}
                      disabled={!selectedKnowId || linkKnowledge.isPending}
                      className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-[4px] text-black transition-opacity disabled:opacity-40"
                      style={{ background: 'var(--venom-yellow)' }}
                    >
                      {linkKnowledge.isPending && <Loader2 size={11} className="animate-spin" />}
                      Link
                    </button>
                  </div>
                )}
              </DrawerSection>

              {task.subtask_count > 0 && (
                <DrawerSection title={`Subtasks (${task.subtask_count})`} icon={null} action={null}>
                  <p className="text-[12px] text-[var(--text-tertiary)]">
                    Subtask list coming in next iteration.
                  </p>
                </DrawerSection>
              )}

              <div className="pt-4 border-t border-[var(--krait-border)]">
                {confirmDeleteTask ? (
                  <div className="flex items-center justify-between p-2 rounded bg-[var(--color-error)]/10 border border-[var(--color-error)]/20">
                    <span className="text-[12px] text-[var(--text-secondary)]">Delete this task?</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setConfirmDeleteTask(false)}
                        className="text-[11px] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => {
                          deleteTask.mutate(task.id, {
                            onSuccess: () => { setConfirmDeleteTask(false); closeTaskDrawer(); },
                          });
                        }}
                        disabled={deleteTask.isPending}
                        className="flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-[4px] text-white bg-[var(--color-error)] hover:opacity-90 transition-opacity disabled:opacity-40"
                      >
                        {deleteTask.isPending && <Loader2 size={10} className="animate-spin" />}
                        Delete
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmDeleteTask(true)}
                    className="flex items-center gap-1.5 text-[12px] text-[var(--text-tertiary)] hover:text-[var(--color-error)] transition-colors"
                  >
                    <Trash2 size={12} />
                    Delete task
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function MetaField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <span className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
        {label}
      </span>
      <div>{children}</div>
    </div>
  );
}

function DrawerSection({
  title,
  icon,
  action,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  action: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
          {icon}
          {title}
        </div>
        {action}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}
