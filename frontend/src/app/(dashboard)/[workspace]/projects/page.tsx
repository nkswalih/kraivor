'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  KanbanSquare, Plus, LayoutGrid, List,
  Search, Loader2,
} from 'lucide-react';
import { useProjects } from '@/lib/hooks/use-projects';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useProjectsStore } from '@/lib/stores/projects-store';
import { ProjectCard } from '@/components/features/projects/project-card';
import { CreateProjectDialog } from '@/components/features/projects/create-project-dialog';
import type { Project, ProjectStatus } from '@/types/domain/projects';
import { cn } from '@/lib/utils';

const STATUS_BADGE: Record<string, { text: string; className: string }> = {
  planning:  { text: 'Planning',  className: 'text-[var(--text-secondary)] bg-[var(--krait-surface-3)] border-[var(--krait-border)]' },
  active:    { text: 'Active',    className: 'text-[var(--venom-yellow)] bg-[var(--venom-glow)] border-[var(--venom-gold)]/30' },
  completed: { text: 'Completed', className: 'text-[var(--color-success)] bg-[var(--color-success)]/10 border-[var(--color-success)]/20' },
  archived:  { text: 'Archived',  className: 'text-[var(--text-tertiary)] bg-[var(--krait-surface-2)] border-[var(--krait-border)]' },
};

const STATUS_FILTERS: { label: string; value: ProjectStatus | undefined }[] = [
  { label: 'All',       value: undefined },
  { label: 'Active',    value: 'active' },
  { label: 'Planning',  value: 'planning' },
  { label: 'Completed', value: 'completed' },
  { label: 'Archived',  value: 'archived' },
];

export default function ProjectsPage() {
  const { workspace } = useParams<{ workspace: string }>();
  const workspaceId = useAuthStore(s => s.workspaceId) ?? workspace;
  const [search, setSearch] = useState('');

  const {
    viewMode,
    projectStatusFilter,
    setViewMode,
    setProjectStatusFilter,
    openCreateProject,
    createProjectOpen,
    closeCreateProject,
  } = useProjectsStore();

  const { data: projects, isLoading } = useProjects(workspaceId, projectStatusFilter);

  const filtered = (projects ?? []).filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-[var(--krait-border)] shrink-0 bg-[var(--krait-obsidian)]">
        <div className="flex items-center gap-4">
          <h1 className="text-[15px] font-medium text-[var(--text-primary)] flex items-center gap-2">
            <KanbanSquare size={17} className="text-[var(--venom-yellow)]" />
            Projects
          </h1>
          <div className="h-4 w-px bg-[var(--krait-border)]" />
          <div className="flex items-center gap-0.5">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.label}
                onClick={() => setProjectStatusFilter(f.value)}
                className={cn(
                  'text-[12px] font-medium px-2.5 py-1 rounded-[4px] transition-colors',
                  projectStatusFilter === f.value
                    ? 'bg-[var(--krait-surface-3)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[6px] p-0.5">
            {(['grid', 'list'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  'p-1.5 rounded transition-colors',
                  viewMode === mode
                    ? 'bg-[var(--krait-surface-3)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                )}
              >
                {mode === 'grid' ? <LayoutGrid size={14} /> : <List size={14} />}
              </button>
            ))}
          </div>

          <button
            onClick={openCreateProject}
            className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-black transition-colors"
            style={{ background: 'var(--venom-yellow)' }}
          >
            <Plus size={13} />
            New Project
          </button>
        </div>
      </div>

      <div className="px-6 py-3 border-b border-[var(--krait-border)] bg-[var(--krait-obsidian)]">
        <div className="relative max-w-sm">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="w-full bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[6px] pl-8 pr-3 py-2 text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-[var(--krait-border-hi)] transition-colors"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-[var(--krait-void)]">
        {isLoading && (
          <div className="flex items-center justify-center h-40">
            <Loader2 size={20} className="animate-spin text-[var(--venom-yellow)]" />
          </div>
        )}

        {!isLoading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-center">
            <KanbanSquare size={32} className="text-[var(--text-tertiary)] mb-3" />
            <p className="text-[14px] text-[var(--text-secondary)]">No projects yet</p>
            <p className="text-[12px] text-[var(--text-tertiary)] mt-1">
              Create your first project to start tracking work.
            </p>
            <button
              onClick={openCreateProject}
              className="mt-4 text-[12px] font-medium px-3 py-1.5 rounded-[6px] text-black"
              style={{ background: 'var(--venom-yellow)' }}
            >
              New Project
            </button>
          </div>
        )}

        {!isLoading && filtered.length > 0 && (
          viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filtered.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  workspaceSlug={workspace}
                />
              ))}
            </div>
          ) : (
            <div className="max-w-3xl space-y-0 border border-[var(--krait-border)] rounded-[8px] bg-[var(--krait-surface-1)] overflow-hidden divide-y divide-[var(--krait-border)]">
              {filtered.map((project) => (
                <ProjectListRow
                  key={project.id}
                  project={project}
                  workspaceSlug={workspace}
                />
              ))}
            </div>
          )
        )}
      </div>

      <CreateProjectDialog
        open={createProjectOpen}
        onClose={closeCreateProject}
        workspaceId={workspaceId}
      />
    </div>
  );
}

function ProjectListRow({ project, workspaceSlug }: { project: Project; workspaceSlug: string }) {
  const badge = STATUS_BADGE[project.status];
  return (
    <Link
      href={`/${workspaceSlug}/projects/${project.id}`}
      className="flex items-center gap-4 px-5 py-3 hover:bg-[var(--krait-surface-2)] transition-colors group"
    >
      <span className="text-[16px] w-6 shrink-0">{project.icon || '\uD83D\uDCCB'}</span>
      <span className="flex-1 text-[13px] text-[var(--text-primary)] group-hover:text-[var(--venom-yellow)] transition-colors truncate">
        {project.name}
      </span>
      <span className={cn('text-[11px] px-2 py-0.5 rounded border', badge.className)}>
        {badge.text}
      </span>
      <span className="text-[12px] text-[var(--text-secondary)] w-16 text-right">
        {project.task_count} tasks
      </span>
      {project.blocked_task_count > 0 && (
        <span className="text-[11px] text-[var(--color-error)] w-16 text-right">
          {project.blocked_task_count} blocked
        </span>
      )}
    </Link>
  );
}
