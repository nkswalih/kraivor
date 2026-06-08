'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Plus, Loader2, ExternalLink, Trash2 } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { knowledgeEndpoints } from '@/lib/api/endpoints';
import { CreateKnowledgeDialog } from '@/components/features/create-knowledge-dialog';
import { formatRelativeTime } from '@/lib/utils';
import { SkeletonCard } from '@/components/ui/skeletons';

export default function KnowledgePage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);
  const [showCreate, setShowCreate] = useState(false);

  const { data: spaces, isLoading } = useQuery({
    queryKey: ['knowledge', workspaceId],
    queryFn: () => knowledgeEndpoints.list(workspaceId!),
    enabled: !!workspaceId,
  });

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <h1 className="text-lg font-medium flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-venom-yellow" /> Knowledge Spaces
        </h1>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-shimmer text-text-inverse text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Create Space
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : (!spaces || spaces.length === 0) ? (
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {spaces.map((space) => (
              <a
                key={space.id}
                href={`/${workspaceSlug}/knowledge/${space.id}`}
                className="block p-4 rounded-lg border border-border bg-krait-surface1 hover:bg-krait-surface2 transition-colors group"
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
                  <ExternalLink className="w-3.5 h-3.5 text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/50">
                  <span className="text-[11px] text-text-tertiary">
                    Created {formatRelativeTime(space.created_at)}
                  </span>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      <CreateKnowledgeDialog open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}
