'use client';

import { useState } from 'react';
import { BookOpen, Plus, Loader2, Search, ExternalLink, Trash2, MoreHorizontal } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useKnowledgeList, useDeleteKnowledge } from '@/lib/hooks/use-knowledge';
import { CreateKnowledgeDialog } from '@/components/features/create-knowledge-dialog';
import { SkeletonCard } from '@/components/ui/skeletons';

export default function KnowledgePage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');

  const { data: spaces, isLoading } = useKnowledgeList(workspaceId ?? undefined, search || undefined);

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
          className="btn-shimmer text-text-inverse text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Create Space
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : (!spaces || spaces.length === 0) ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <BookOpen className="w-10 h-10 text-muted-foreground mb-3" />
            <h3 className="text-base font-medium text-foreground mb-1">No knowledge spaces</h3>
            <p className="text-[13px] text-muted-foreground max-w-xs mb-4">
              {search ? 'No spaces match your search.' : 'Create a knowledge space to organize your team\'s documentation and context.'}
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
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {spaces.map((space) => (
              <KnowledgeCard
                key={space.id}
                space={space}
                workspaceSlug={workspaceSlug}
              />
            ))}
          </div>
        )}
      </div>

      <CreateKnowledgeDialog open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}

function KnowledgeCard({ space, workspaceSlug }: { space: { id: string; name: string; description: string | null; created_at: string }; workspaceSlug: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const workspaceId = useAuthStore(s => s.workspaceId);
  const deleteMut = useDeleteKnowledge(space.id, workspaceId ?? '');

  return (
    <a
      href={`/${workspaceSlug}/knowledge/${space.id}`}
      className="block p-4 rounded-lg border border-border bg-krait-surface1 hover:bg-krait-surface2 transition-colors group relative"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-venom-yellow/10 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-venom-yellow" />
          </div>
          <div>
            <h3 className="text-[14px] font-medium text-foreground">{space.name}</h3>
            {space.description && (
              <p className="text-[12px] text-text-tertiary line-clamp-1">{space.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <ExternalLink className="w-3.5 h-3.5 text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative">
            <button
              onClick={e => { e.preventDefault(); setMenuOpen(!menuOpen); }}
              className="p-1 text-text-tertiary hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreHorizontal className="w-3.5 h-3.5" />
            </button>
            {menuOpen && (
              <div
                className="absolute right-0 top-full mt-1 w-32 py-1 rounded-lg border border-border bg-krait-surface2 shadow-lg z-10"
                onClick={e => e.preventDefault()}
              >
                <button
                  onClick={() => { deleteMut.mutate(); setMenuOpen(false); }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-red-400 hover:bg-krait-surface3"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/50">
        <span className="text-[11px] text-text-tertiary">
          {new Date(space.created_at).toLocaleDateString()}
        </span>
      </div>
    </a>
  );
}
