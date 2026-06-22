'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Loader2, Trash2 } from 'lucide-react';
import { useProject, useProjectTasks, useDeleteProject } from '@/lib/hooks/use-projects';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useProjectsStore } from '@/lib/stores/projects-store';
import { TaskRow } from '@/components/features/tasks/task-row';
import { TaskDrawer } from '@/components/features/tasks/task-drawer';
import { CreateTaskDialog } from '@/components/features/tasks/create-task-dialog';
import { ProjectBoardTab } from '@/components/features/projects/project-board-tab';
import { ProjectOverviewTab } from '@/components/features/projects/project-overview-tab';
import { ProjectInsightsTab } from '@/components/features/projects/project-insights-tab';
import { EditProjectDialog } from '@/components/features/projects/edit-project-dialog';
import { cn } from '@/lib/utils';
import type { Task } from '@/types/domain/projects';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'board', label: 'Board' },
  { id: 'list', label: 'List' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'insights', label: 'Insights' },
] as const;

function ProjectTimelineTab({ tasks }: { tasks: Task[] }) {
  const allStatuses = [
    'backlog',
    'todo',
    'in_progress',
    'in_review',
    'blocked',
    'done',
    'cancelled',
  ] as const;
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-[14px] font-medium text-[var(--text-primary)]">Timeline</h2>
        <span className="text-[11px] text-[var(--text-tertiary)] border border-[var(--krait-border)] px-1.5 py-0.5 rounded">
          CSS Gantt
        </span>
      </div>
      <div className="space-y-0.5">
        {tasks.length === 0 && (
          <p className="text-[13px] text-[var(--text-tertiary)]">No tasks to display.</p>
        )}
        {tasks.slice(0, 20).map(task => {
          const idx = allStatuses.indexOf(task.status);
          const leftPct = (idx / allStatuses.length) * 100;
          return (
            <div
              key={task.id}
              className="flex items-center gap-3 py-2 px-3 bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[6px]"
            >
              <span className="text-[12px] text-[var(--text-primary)] flex-1 truncate min-w-0">
                {task.title}
              </span>
              <div className="relative w-32 h-3 bg-[var(--krait-surface-3)] rounded-full overflow-hidden shrink-0">
                <div
                  className="absolute top-0 h-full rounded-full"
                  style={{
                    left: `${leftPct}%`,
                    width: `${100 / allStatuses.length}%`,
                    background: 'var(--venom-yellow)',
                  }}
                />
              </div>
              <span className="text-[10px] text-[var(--text-tertiary)] w-16 text-right shrink-0 capitalize">
                {task.status.replace('_', ' ')}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ProjectDetailPage() {
  const { workspace, projectId } = useParams<{
    workspace: string;
    projectId: string;
  }>();
  const router = useRouter();
  const workspaceId = useAuthStore(s => s.workspaceId) ?? workspace;

  const { data: project, isLoading: projectLoading } = useProject(workspaceId, projectId);
  const { data: tasksData, isLoading: tasksLoading } = useProjectTasks(workspaceId, projectId);
  const tasks: Task[] = tasksData?.results ?? [];
  const deleteProject = useDeleteProject(workspaceId);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const searchParams = useSearchParams();

  useEffect(() => {
    const taskId = searchParams.get('task');
    if (taskId && !tasksLoading && tasks.length > 0) {
      useProjectsStore.getState().openTaskDrawer(taskId);
    }
  }, [searchParams, tasksLoading, tasks]);

  const {
    activeTab,
    setActiveTab,
    createTaskOpen,
    createTaskDefaultProjectId,
    closeCreateTask,
    openCreateTask,
    editProjectOpen,
    closeEditProject,
    openEditProject,
  } = useProjectsStore();

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={20} className="animate-spin text-[var(--venom-yellow)]" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-secondary)]">
        Project not found.
      </div>
    );
  }

  const progress =
    project.task_count > 0 ? Math.round((project.done_task_count / project.task_count) * 100) : 0;

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 pt-5 pb-0 border-b border-[var(--krait-border)] bg-[var(--krait-obsidian)]">
        <Link
          href={`/${workspace}/projects`}
          className="inline-flex items-center gap-1.5 text-[12px] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] mb-4 transition-colors"
        >
          <ArrowLeft size={12} />
          Projects
        </Link>

        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-[24px]">{project.icon || '\uD83D\uDCCB'}</span>
            <div>
              <h1 className="text-[20px] font-semibold text-[var(--text-primary)]">
                {project.name}
              </h1>
              {project.description && (
                <p className="text-[13px] text-[var(--text-secondary)] mt-0.5">
                  {project.description}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <div className="text-[20px] font-semibold text-[var(--text-primary)]">
                {progress}%
              </div>
              <div className="text-[11px] text-[var(--text-tertiary)]">complete</div>
            </div>
            <button
              onClick={() => openEditProject(projectId)}
              className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-[var(--text-secondary)] border border-[var(--krait-border)] hover:bg-[var(--krait-surface-2)] transition-colors"
            >
              Edit
            </button>
            <button
              onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-[var(--color-error)] border border-[var(--color-error)]/30 hover:bg-[var(--color-error)]/10 transition-colors"
            >
              <Trash2 size={12} />
              Delete
            </button>
            <button
              onClick={() => openCreateTask(projectId)}
              className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-black"
              style={{ background: 'var(--venom-yellow)' }}
            >
              + New Issue
            </button>
          </div>
        </div>

        <div className="flex items-center gap-0.5">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-3.5 py-2.5 text-[13px] font-medium transition-colors border-b-2',
                activeTab === tab.id
                  ? 'border-[var(--venom-yellow)] text-[var(--text-primary)]'
                  : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-[var(--krait-void)]">
        {activeTab === 'overview' && <ProjectOverviewTab project={project} tasks={tasks} />}
        {activeTab === 'board' && (
          <ProjectBoardTab
            workspaceId={workspaceId}
            projectId={projectId}
            tasks={tasks}
            isLoading={tasksLoading}
          />
        )}
        {activeTab === 'list' && (
          <div className="py-2">
            {tasks.map((task, i) => (
              <TaskRow
                key={task.id}
                task={task}
                identifier={`KRV-${String(i + 1).padStart(2, '0')}`}
              />
            ))}
          </div>
        )}
        {activeTab === 'timeline' && <ProjectTimelineTab tasks={tasks} />}
        {activeTab === 'insights' && (
          <ProjectInsightsTab workspaceId={workspaceId} projectId={projectId} />
        )}
      </div>

      <TaskDrawer workspaceId={workspaceId} />
      <CreateTaskDialog
        open={createTaskOpen}
        onClose={closeCreateTask}
        workspaceId={workspaceId}
        defaultProjectId={createTaskDefaultProjectId ?? projectId}
      />
      <EditProjectDialog
        open={editProjectOpen}
        onClose={closeEditProject}
        workspaceId={workspaceId}
        projectId={projectId}
      />

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setConfirmDelete(false)} />
          <div className="relative w-full max-w-sm bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[10px] p-5 shadow-2xl">
            <h3 className="text-[14px] font-medium text-[var(--text-primary)] mb-2">
              Delete project?
            </h3>
            <p className="text-[13px] text-[var(--text-secondary)] mb-5">
              This will permanently delete{' '}
              <strong className="text-[var(--text-primary)]">{project.name}</strong> and all its
              tasks. This action cannot be undone.
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setConfirmDelete(false)}
                className="text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-[var(--text-secondary)] border border-[var(--krait-border)] hover:bg-[var(--krait-surface-2)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteProject.mutate(projectId, {
                    onSuccess: () => router.push(`/${workspace}/projects`),
                  });
                }}
                disabled={deleteProject.isPending}
                className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-white bg-[var(--color-error)] hover:opacity-90 transition-opacity disabled:opacity-40"
              >
                {deleteProject.isPending && <Loader2 size={12} className="animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
