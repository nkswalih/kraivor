'use client';

import type { Project, Task } from '@/types/domain/projects';
import { GitBranch, BookOpen, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { TERMINAL_TASK_STATUSES } from '@/types/domain/projects';

interface ProjectOverviewTabProps {
  project: Project;
  tasks: Task[];
}

export function ProjectOverviewTab({ project, tasks }: ProjectOverviewTabProps) {
  const done = tasks.filter((t) => t.status === 'done').length;
  const blocked = tasks.filter((t) => t.status === 'blocked').length;
  const active = tasks.filter((t) => !TERMINAL_TASK_STATUSES.includes(t.status) && t.status !== 'backlog').length;
  const progress = project.task_count > 0 ? Math.round((done / project.task_count) * 100) : 0;

  return (
    <div className="p-6 max-w-4xl space-y-8">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total" value={project.task_count} icon={<CheckCircle size={16} className="text-[var(--venom-yellow)]" />} />
        <StatCard label="Active" value={active} icon={<Clock size={16} className="text-[var(--color-info)]" />} />
        <StatCard label="Done" value={done} icon={<CheckCircle size={16} className="text-[var(--color-success)]" />} />
        <StatCard label="Blocked" value={blocked} accent={blocked > 0} icon={<AlertCircle size={16} className="text-[var(--color-error)]" />} />
      </div>

      <div>
        <div className="flex justify-between text-[12px] text-[var(--text-secondary)] mb-2">
          <span>Overall Progress</span>
          <span className="font-medium text-[var(--text-primary)]">{progress}%</span>
        </div>
        <div className="h-2 bg-[var(--krait-surface-3)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, var(--venom-gold), var(--venom-yellow))',
            }}
          />
        </div>
      </div>

      {project.repository && (
        <div>
          <h3 className="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-wider mb-3">
            Repository
          </h3>
          <div className="flex items-center gap-3 bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[8px] px-4 py-3">
            <GitBranch size={16} className="text-[var(--venom-yellow)] shrink-0" />
            <span className="text-[13px] text-[var(--text-primary)]">
              {project.repository.github_repo}
            </span>
          </div>
        </div>
      )}

      {project.knowledge_space && (
        <div>
          <h3 className="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-wider mb-3">
            Knowledge
          </h3>
          <div className="flex items-center gap-3 bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[8px] px-4 py-3">
            <BookOpen size={16} className="text-[var(--venom-yellow)] shrink-0" />
            <span className="text-[13px] text-[var(--text-primary)]">
              {project.knowledge_space.name}
            </span>
          </div>
        </div>
      )}

      <div>
        <h3 className="text-[12px] font-medium text-[var(--text-secondary)] uppercase tracking-wider mb-3">
          Recently Updated
        </h3>
        <div className="space-y-1 border border-[var(--krait-border)] rounded-[8px] bg-[var(--krait-surface-1)] divide-y divide-[var(--krait-border)]/50 overflow-hidden">
          {tasks
            .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
            .slice(0, 5)
            .map((task) => (
              <div key={task.id} className="flex items-center gap-3 px-4 py-2.5 text-[13px]">
                <span className="text-[var(--text-primary)] flex-1 truncate">{task.title}</span>
                <span className="text-[11px] text-[var(--text-tertiary)] capitalize shrink-0">
                  {task.status.replace('_', ' ')}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  accent = false,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[8px] px-4 py-3">
      <div className="flex items-center justify-between mb-1">
        {icon}
        <span className={`text-[22px] font-semibold ${accent ? 'text-[var(--color-error)]' : 'text-[var(--text-primary)]'}`}>
          {value}
        </span>
      </div>
      <span className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">{label}</span>
    </div>
  );
}
