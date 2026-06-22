'use client';

import { useState, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';
import {
  useUpdateProject,
  useProject,
  useRepositoriesList,
  useKnowledgeSpacesList,
} from '@/lib/hooks/use-projects';
import type { ProjectStatus, ProjectVisibility } from '@/types/domain/projects';

interface EditProjectDialogProps {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  projectId: string;
}

export function EditProjectDialog({
  open,
  onClose,
  workspaceId,
  projectId,
}: EditProjectDialogProps) {
  const { data: project, isLoading } = useProject(workspaceId, projectId);
  const { data: repos } = useRepositoriesList(workspaceId);
  const { data: knowledgeSpaces } = useKnowledgeSpacesList(workspaceId);
  const updateProject = useUpdateProject(workspaceId, projectId);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [icon, setIcon] = useState('');
  const [color, setColor] = useState('');
  const [status, setStatus] = useState<ProjectStatus>('planning');
  const [visibility, setVisibility] = useState<ProjectVisibility>('workspace');
  const [repositoryId, setRepositoryId] = useState<string | null>(null);
  const [knowledgeSpaceId, setKnowledgeSpaceId] = useState<string | null>(null);

  useEffect(() => {
    if (project) {
      setName(project.name);
      setDescription(project.description);
      setIcon(project.icon);
      setColor(project.color);
      setStatus(project.status);
      setVisibility(project.visibility);
      setRepositoryId(project.repository?.id ?? null);
      setKnowledgeSpaceId(project.knowledge_space?.id ?? null);
    }
  }, [project]);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    await updateProject.mutateAsync({
      name: name.trim(),
      description: description || undefined,
      icon: icon || undefined,
      color: color || undefined,
      status,
      visibility,
      repository_id: repositoryId,
      knowledge_space_id: knowledgeSpaceId,
    });
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative w-full max-w-lg bg-[var(--krait-surface-1)] border border-[var(--krait-border)] rounded-[10px] p-5 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[14px] font-medium text-[var(--text-primary)]">Edit Project</h2>
          <button
            onClick={onClose}
            className="p-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--krait-surface-3)] transition-colors"
          >
            <X size={15} />
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={18} className="animate-spin text-[var(--venom-yellow)]" />
          </div>
        ) : (
          <>
            <div className="space-y-4 mb-5">
              <input
                autoFocus
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleSubmit();
                  if (e.key === 'Escape') onClose();
                }}
                placeholder="Project name"
                className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] rounded-[6px] px-3 py-2 text-[14px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none focus:border-[var(--krait-border-hi)]"
              />

              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Description (optional)"
                rows={2}
                className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] rounded-[6px] px-3 py-2 text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none focus:border-[var(--krait-border-hi)] resize-none"
              />

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
                    Icon
                  </label>
                  <input
                    value={icon}
                    onChange={e => setIcon(e.target.value)}
                    placeholder="Emoji"
                    maxLength={2}
                    className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] rounded-[6px] px-3 py-2 text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none focus:border-[var(--krait-border-hi)]"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
                    Color
                  </label>
                  <input
                    value={color}
                    onChange={e => setColor(e.target.value)}
                    placeholder="#RRGGBB"
                    maxLength={7}
                    className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] rounded-[6px] px-3 py-2 text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none focus:border-[var(--krait-border-hi)]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
                    Status
                  </label>
                  <select
                    value={status}
                    onChange={e => setStatus(e.target.value as ProjectStatus)}
                    className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[6px] px-3 py-2 text-[13px] outline-none focus:border-[var(--krait-border-hi)]"
                  >
                    {(['planning', 'active', 'completed', 'archived'] as const).map(s => (
                      <option key={s} value={s} className="capitalize">
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
                    Visibility
                  </label>
                  <select
                    value={visibility}
                    onChange={e => setVisibility(e.target.value as ProjectVisibility)}
                    className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[6px] px-3 py-2 text-[13px] outline-none focus:border-[var(--krait-border-hi)]"
                  >
                    <option value="workspace">Workspace</option>
                    <option value="private">Private</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
                    Repository
                  </label>
                  <select
                    value={repositoryId ?? ''}
                    onChange={e => setRepositoryId(e.target.value || null)}
                    className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[6px] px-3 py-2 text-[13px] outline-none focus:border-[var(--krait-border-hi)]"
                  >
                    <option value="">None</option>
                    {(repos ?? []).map(r => (
                      <option key={r.id} value={r.id}>
                        {r.github_repo}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] text-[var(--text-tertiary)] uppercase tracking-wider">
                    Knowledge Space
                  </label>
                  <select
                    value={knowledgeSpaceId ?? ''}
                    onChange={e => setKnowledgeSpaceId(e.target.value || null)}
                    className="w-full bg-[var(--krait-surface-2)] border border-[var(--krait-border)] text-[var(--text-secondary)] rounded-[6px] px-3 py-2 text-[13px] outline-none focus:border-[var(--krait-border-hi)]"
                  >
                    <option value="">None</option>
                    {(knowledgeSpaces ?? []).map(k => (
                      <option key={k.id} value={k.id}>
                        {k.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-[var(--krait-border)] pt-3">
              <span className="text-[11px] text-[var(--text-tertiary)]">
                Press Enter to save - Esc to cancel
              </span>
              <button
                onClick={handleSubmit}
                disabled={!name.trim() || updateProject.isPending}
                className="flex items-center gap-2 text-[12px] font-medium px-3.5 py-1.5 rounded-[6px] text-black transition-opacity disabled:opacity-40"
                style={{ background: 'var(--venom-yellow)' }}
              >
                {updateProject.isPending && <Loader2 size={12} className="animate-spin" />}
                Save Changes
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
