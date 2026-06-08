'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Edit3, Trash2, Loader2, ArrowLeft, Save, X } from 'lucide-react';
import { knowledgeEndpoints } from '@/lib/api/endpoints';
import { formatRelativeTime } from '@/lib/utils';
import { SkeletonBlock, SkeletonLine } from '@/components/ui/skeletons';

export default function KnowledgeDetailPage() {
  const params = useParams<{ id: string; workspace: string }>();
  const id = params?.id ?? '';
  const workspaceSlug = params?.workspace ?? '';
  const queryClient = useQueryClient();

  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');

  const { data: space, isLoading } = useQuery({
    queryKey: ['knowledge', id],
    queryFn: () => knowledgeEndpoints.get(id),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      knowledgeEndpoints.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge', id] });
      setEditing(false);
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => knowledgeEndpoints.delete(id),
    onSuccess: () => {
      window.location.href = `/${workspaceSlug}/knowledge`;
    },
  });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full animate-fade-up">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-3">
            <SkeletonBlock className="w-8 h-8 rounded" />
            <SkeletonLine className="w-40 h-5" />
          </div>
        </div>
        <div className="flex-1 p-6 space-y-4">
          <SkeletonBlock className="w-full h-24 rounded-lg" />
          <SkeletonBlock className="w-full h-32 rounded-lg" />
          <SkeletonBlock className="w-full h-40 rounded-lg" />
        </div>
      </div>
    );
  }

  if (!space) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <BookOpen className="w-10 h-10 text-muted-foreground mb-3" />
        <h3 className="text-base font-medium text-foreground mb-1">Space not found</h3>
        <a href={`/${workspaceSlug}/knowledge`} className="text-[13px] text-venom-yellow hover:text-venom-gold mt-2">
          Back to knowledge spaces
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <a
            href={`/${workspaceSlug}/knowledge`}
            className="p-1.5 text-text-tertiary hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </a>
          {editing ? (
            <div className="flex items-center gap-2">
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="px-2 py-1 bg-krait-surface3 border border-border rounded text-[15px] font-medium text-foreground focus:outline-none focus:border-venom-yellow/50"
                autoFocus
              />
            </div>
          ) : (
            <h1 className="text-lg font-medium text-foreground">{space.name}</h1>
          )}
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <button
                onClick={() => updateMut.mutate({ name: editName, description: editDesc || undefined })}
                disabled={updateMut.isPending || !editName.trim()}
                className="px-3 py-1.5 bg-venom-yellow text-black text-[12px] font-medium rounded-lg hover:brightness-110 transition-all disabled:opacity-50 flex items-center gap-1"
              >
                {updateMut.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="p-1.5 text-text-tertiary hover:text-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => { setEditName(space.name); setEditDesc(space.description ?? ''); setEditing(true); }}
                className="p-1.5 text-text-tertiary hover:text-foreground transition-colors"
                title="Edit"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => { if (confirm('Delete this knowledge space?')) deleteMut.mutate(); }}
                disabled={deleteMut.isPending}
                className="p-1.5 text-text-tertiary hover:text-red-400 transition-colors"
                title="Delete"
              >
                {deleteMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Description */}
        <div className="rounded-lg border border-border bg-krait-surface1 p-4">
          <h4 className="text-[12px] font-semibold tracking-wider text-text-tertiary uppercase mb-2">Description</h4>
          {editing ? (
            <textarea
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 bg-krait-surface3 border border-border rounded-lg text-[13px] text-foreground placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 resize-none"
              placeholder="Add a description..."
            />
          ) : (
            <p className="text-[13px] text-text-secondary whitespace-pre-wrap">
              {space.description || 'No description added yet.'}
            </p>
          )}
        </div>

        {/* Metadata */}
        <div className="rounded-lg border border-border bg-krait-surface1 p-4">
          <h4 className="text-[12px] font-semibold tracking-wider text-text-tertiary uppercase mb-3">Details</h4>
          <div className="space-y-2 text-[13px]">
            <div className="flex justify-between">
              <span className="text-text-tertiary">Created</span>
              <span className="text-foreground">{formatRelativeTime(space.created_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">Last updated</span>
              <span className="text-foreground">{formatRelativeTime(space.updated_at)}</span>
            </div>
          </div>
        </div>

        {/* Canvas area (placeholder for future) */}
        <div className="rounded-lg border border-border bg-krait-surface1 p-4">
          <h4 className="text-[12px] font-semibold tracking-wider text-text-tertiary uppercase mb-2">Canvas</h4>
          {space.canvas_data ? (
            <pre className="text-[12px] text-text-secondary">{JSON.stringify(space.canvas_data, null, 2)}</pre>
          ) : (
            <p className="text-[13px] text-text-tertiary">No canvas data yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
