'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import {
  BookOpen,
  Plus,
  Loader2,
  Search,
  ExternalLink,
  Trash2,
  MoreHorizontal,
  Check,
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
  const [search, setSearch] = useState('');

  const { data: spaces, isLoading } = useKnowledgeList(
    workspaceId ?? undefined,
    search || undefined
  );

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
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-medium flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-venom-yellow" /> Knowledge Spaces
          </h1>
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search spaces..."
              className="pl-8 pr-3 py-1.5 w-48 bg-krait-surface3 border border-border rounded-lg text-[12px] text-foreground placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50"
            />
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-venom-yellow hover:bg-primary-light text-black text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Create Space
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
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
              {search
                ? 'No spaces match your search.'
                : "Create a knowledge space to organize your team's documentation and context."}
            </p>
            {!search && (
              <button
                onClick={() => setShowCreate(true)}
                className="btn-shimmer text-text-inverse text-[12px] font-medium py-2 px-4 rounded flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" /> Create Knowledge Space
              </button>
            )}
          </div>
        ) : search ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {spaces.map(space => (
              <KnowledgeCard key={space.id} space={space} workspaceSlug={workspaceSlug} />
            ))}
          </div>
        ) : (
          <div>
            {groupedSpaces.map(([category, categorySpaces]) => (
              <div key={category} className="mb-8">
                <h2 className="text-base font-semibold text-foreground mb-3">{category}</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {categorySpaces.map(space => (
                    <KnowledgeCard key={space.id} space={space} workspaceSlug={workspaceSlug} />
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

function KnowledgeCard({
  space,
  workspaceSlug,
}: {
  space: {
    id: string;
    name: string;
    description: string | null;
    created_at: string;
    updated_at: string;
  };
  workspaceSlug: string;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState<'name' | 'description' | null>(null);
  const [editValue, setEditValue] = useState('');
  const workspaceId = useAuthStore(s => s.workspaceId);
  const deleteMut = useDeleteKnowledge(space.id, workspaceId ?? '');
  const updateMut = useUpdateKnowledge(space.id, workspaceId ?? '');
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const startEdit = (field: 'name' | 'description') => {
    setEditing(field);
    setEditValue(field === 'name' ? space.name : (space.description ?? ''));
  };

  const saveEdit = () => {
    if (!editing) return;
    const trimmed = editValue.trim();
    const payload: { name: string; description?: string } = {
      name: space.name,
      description: space.description ?? '',
    };
    if (editing === 'name') payload.name = trimmed || space.name;
    else payload.description = trimmed;
    updateMut.mutate(payload);
    setEditing(null);
    setEditValue('');
    setMenuOpen(false);
  };

  const cancelEdit = () => {
    setEditing(null);
    setEditValue('');
  };

  return (
    <div
      onClick={() => router.push(`/${workspaceSlug}/knowledge/${space.id}`)}
      className="flex flex-col p-4 rounded-lg border border-border bg-krait-surface1 hover:bg-krait-surface2 transition-colors group relative cursor-pointer"
    >
      <div className="flex items-start justify-between mb-1">
        <div
          className="flex items-center gap-2.5 min-w-0 flex-1"
          onClick={e => e.stopPropagation()}
        >
          <div className="w-8 h-8 rounded-lg bg-venom-yellow/10 flex items-center justify-center shrink-0">
            <BookOpen className="w-4 h-4 text-venom-yellow" />
          </div>
          {editing === 'name' ? (
            <div className="flex items-center gap-1 flex-1">
              <input
                ref={inputRef as React.RefObject<HTMLInputElement>}
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') saveEdit();
                  if (e.key === 'Escape') cancelEdit();
                }}
                onBlur={saveEdit}
                className="flex-1 bg-krait-surface3 border border-border rounded px-1.5 py-0.5 text-[14px] text-foreground focus:outline-none focus:border-venom-yellow/50"
              />
            </div>
          ) : (
            <h3
              onClick={() => startEdit('name')}
              className="text-[14px] font-medium text-foreground truncate hover:text-venom-yellow transition-colors cursor-text"
            >
              {space.name}
            </h3>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
          <ExternalLink
            onClick={e => {
              e.stopPropagation();
              router.push(`/${workspaceSlug}/knowledge/${space.id}`);
            }}
            className="w-3.5 h-3.5 text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer hover:text-venom-yellow"
          />
          <div className="relative">
            <button
              onClick={e => {
                e.preventDefault();
                e.stopPropagation();
                setMenuOpen(!menuOpen);
              }}
              className="p-1 text-text-tertiary hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreHorizontal className="w-3.5 h-3.5" />
            </button>
            {menuOpen && (
              <div
                className="absolute right-0 top-full mt-1 w-32 py-1 rounded-lg border border-border bg-krait-surface2 shadow-lg z-10"
                onClick={e => e.stopPropagation()}
              >
                <button
                  onClick={() => {
                    startEdit('name');
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-text-secondary hover:bg-krait-surface3"
                >
                  <BookOpen className="w-3 h-3" /> Rename
                </button>
                <button
                  onClick={() => {
                    deleteMut.mutate();
                    setMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-red-400 hover:bg-krait-surface3"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="flex-1" onClick={e => e.stopPropagation()}>
        {editing === 'description' ? (
          <div className="flex items-start gap-1 mb-3">
            <textarea
              ref={inputRef as React.RefObject<HTMLTextAreaElement>}
              value={editValue}
              onChange={e => setEditValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Escape') cancelEdit();
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  saveEdit();
                }
              }}
              onBlur={saveEdit}
              rows={2}
              className="flex-1 bg-krait-surface3 border border-border rounded px-1.5 py-1 text-[12px] text-foreground resize-none focus:outline-none focus:border-venom-yellow/50"
            />
          </div>
        ) : (
          <p
            onClick={() => startEdit('description')}
            className={`text-[12px] line-clamp-2 mb-3 transition-colors cursor-text ${space.description ? 'text-text-tertiary' : 'text-text-tertiary/40 italic'}`}
          >
            {space.description || 'Add description...'}
          </p>
        )}
      </div>
      <div className="flex items-center justify-between pt-2 border-t border-border/50">
        <span className="text-[11px] text-text-tertiary">
          Updated {formatRelativeTime(space.updated_at)}
        </span>
      </div>
    </div>
  );
}
