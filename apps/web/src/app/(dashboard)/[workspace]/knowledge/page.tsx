'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import {
  BookOpen,
  Plus,
  Loader2,
  Trash2,
  MoreHorizontal,
  Pencil,
  X,
} from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import {
  useKnowledgeList,
  useDeleteKnowledge,
  useUpdateKnowledge,
} from '@/lib/hooks/use-knowledge';
import { CreateKnowledgeDialog } from '@/components/features/create-knowledge-dialog';
import { SkeletonCard } from '@/components/ui/skeletons';
import { formatRelativeTime } from '@/lib/utils';

function getTimeCategory(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays <= 7) return 'Previous 7 days';
  if (diffDays <= 30) return 'Previous 30 days';

  const month = date.toLocaleDateString('en-US', { month: 'long' });
  const year = date.getFullYear();
  return year === now.getFullYear() ? month : `${month} ${year}`;
}

const CATEGORY_ORDER = ['Previous 7 days', 'Previous 30 days'];

function categorySortKey(cat: string): string {
  const idx = CATEGORY_ORDER.indexOf(cat);
  if (idx !== -1) return `0-${idx}`;
  const d = new Date(`${cat} 1, ${new Date().getFullYear()}`);
  if (!isNaN(d.getTime())) return `1-${99999999999 - d.getTime()}`;
  return '1-0';
}

export default function KnowledgePage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);
  const [showCreate, setShowCreate] = useState(false);

  const { data: spaces, isLoading } = useKnowledgeList(workspaceId ?? undefined);

  const groupedSpaces = useMemo(() => {
    if (!spaces) return [];
    const groups: Record<string, typeof spaces> = {};
    for (const space of spaces) {
      const category = getTimeCategory(space.updated_at);
      if (!groups[category]) groups[category] = [];
      groups[category].push(space);
    }
    return Object.entries(groups).sort(([a], [b]) =>
      categorySortKey(a).localeCompare(categorySortKey(b))
    );
  }, [spaces]);

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <h1 className="text-lg font-medium flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-venom-yellow" /> Knowledge Spaces
        </h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-venom-yellow hover:bg-primary-light text-black text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Create Space
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 relative">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.07) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : !spaces || spaces.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <BookOpen className="w-10 h-10 text-muted-foreground mb-3" />
            <h3 className="text-base font-medium text-foreground mb-1">No knowledge spaces</h3>
            <p className="text-[13px] text-muted-foreground max-w-xs mb-4">
              Create a knowledge space to organize your team&apos;s documentation and context.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="btn-shimmer text-text-inverse text-[12px] font-medium py-2 px-4 rounded flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" /> Create Knowledge Space
            </button>
          </div>
        ) : (
          <div>
            {groupedSpaces.map(([category, categorySpaces]) => (
              <div key={category} className="mb-8">
                <h2 className="text-base font-semibold text-foreground mb-3">{category}</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {categorySpaces.map((space, i) => (
                    <KnowledgeCard
                      key={space.id}
                      space={space}
                      workspaceSlug={workspaceSlug}
                      index={i}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <CreateKnowledgeDialog open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}

function RenameDialog({
  open,
  currentName,
  currentDescription,
  onSave,
  onClose,
}: {
  open: boolean;
  currentName: string;
  currentDescription: string;
  onSave: (name: string, description: string) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState(currentName);
  const [description, setDescription] = useState(currentDescription);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setName(currentName);
      setDescription(currentDescription);
    }
  }, [open, currentName, currentDescription]);

  if (!open) return null;

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave(name.trim(), description);
      onClose();
    } catch {
      //
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onMouseDown={e => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl animate-scale-in">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#27272A]">
          <h2 className="text-[15px] font-semibold text-[#FAFAFA] flex items-center gap-2">
            <Pencil className="w-4 h-4 text-venom-yellow" /> Rename Space
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-text-tertiary hover:text-[#FAFAFA] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-text-secondary mb-1.5">Name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Space name"
              className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors"
              autoFocus
              onKeyDown={e => {
                if (e.key === 'Enter') handleSave();
                if (e.key === 'Escape') onClose();
              }}
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-text-secondary mb-1.5">
              Description <span className="text-text-tertiary">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="What is this space for?"
              rows={3}
              className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors resize-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-[13px] text-text-secondary hover:text-[#FAFAFA] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !name.trim()}
              className="px-4 py-1.5 bg-venom-yellow text-black text-[13px] font-medium rounded-lg hover:brightness-110 transition-all disabled:opacity-50 flex items-center gap-1.5"
            >
              {saving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Pencil className="w-3.5 h-3.5" />
              )}
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function KnowledgeCard({
  space,
  workspaceSlug,
  index = 0,
}: {
  space: {
    id: string;
    name: string;
    description: string | null;
    created_at: string;
    updated_at: string;
  };
  workspaceSlug: string;
  index?: number;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showRename, setShowRename] = useState(false);
  const workspaceId = useAuthStore(s => s.workspaceId);
  const deleteMut = useDeleteKnowledge(space.id, workspaceId ?? '');
  const updateMut = useUpdateKnowledge(space.id, workspaceId ?? '');
  const router = useRouter();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const handleDelete = () => {
    if (window.confirm(`Delete "${space.name}"? This cannot be undone.`)) {
      deleteMut.mutate();
    }
    setMenuOpen(false);
  };

  return (
    <>
      <div
        className="animate-fade-up"
        style={{ animationDelay: `${index * 0.04}s` }}
      >
        <div
          onClick={() => router.push(`/${workspaceSlug}/knowledge/${space.id}`)}
          className="group relative bg-card border border-border rounded-lg p-4 cursor-pointer
                     hover:border-venom-yellow/40 hover:shadow-venom
                     transition-all duration-[var(--duration-fast)] ease-strike h-full"
        >
          <div className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full bg-transparent group-hover:bg-venom-yellow transition-all duration-[var(--duration-normal)] ease-strike" />

          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="w-9 h-9 rounded-lg bg-venom-yellow/10 flex items-center justify-center shrink-0 group-hover:bg-venom-yellow/20 group-hover:scale-105 transition-all duration-[var(--duration-fast)]">
                <BookOpen className="w-[18px] h-[18px] text-venom-yellow" />
              </div>
              <div className="min-w-0">
                <h3 className="text-[14px] font-medium text-foreground truncate group-hover:text-venom-yellow transition-colors">
                  {space.name}
                </h3>
                <span className="text-[11px] text-muted-foreground">
                  Updated {formatRelativeTime(space.updated_at)}
                </span>
              </div>
            </div>

            <div ref={menuRef} className="relative shrink-0" onClick={e => e.stopPropagation()}>
              <button
                onClick={e => {
                  e.preventDefault();
                  setMenuOpen(!menuOpen);
                }}
                className="p-1 text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>
              {menuOpen && (
                <div className="absolute right-0 top-full mt-1 w-36 py-1 rounded-lg border border-border bg-popover shadow-lg z-10">
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      setShowRename(true);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-foreground hover:bg-accent"
                  >
                    <Pencil className="w-3.5 h-3.5" /> Rename
                  </button>
                  <button
                    onClick={handleDelete}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-destructive hover:bg-accent"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                </div>
              )}
            </div>
          </div>

          {space.description && (
            <p className="text-[12px] text-muted-foreground mt-3 leading-relaxed line-clamp-2">
              {space.description}
            </p>
          )}
        </div>
      </div>

      <RenameDialog
        open={showRename}
        currentName={space.name}
        currentDescription={space.description ?? ''}
        onSave={async (name, description) => {
          updateMut.mutate({ name, description });
        }}
        onClose={() => setShowRename(false)}
      />
    </>
  );
}
