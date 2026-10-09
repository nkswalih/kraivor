'use client';

import { useUserDiscussions } from '@/lib/hooks/use-profiles';
import { MessageSquare, MessageCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/shadcn';
import { formatRelativeTime } from '@/lib/utils';

interface UserDiscussionListProps {
  userId: string;
  workspaceSlug?: string;
}

export function UserDiscussionList({ userId, workspaceSlug }: UserDiscussionListProps) {
  const { data, isLoading } = useUserDiscussions(userId);
  const discussions = data?.results ?? [];

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <Skeleton key={i} className="h-24 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (discussions.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <MessageCircle className="w-8 h-8 mx-auto mb-3 opacity-40" />
        <p className="text-[13px]">No discussions yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {discussions.map(d => (
        <div
          key={d.id}
          className="bg-card border border-border rounded-lg p-4 hover:border-primary/40 transition-colors"
        >
          <div className="flex gap-4">
            <div className="flex flex-col items-center gap-1 min-w-[40px] text-[12px] text-muted-foreground">
              <MessageSquare className="w-4 h-4" />
              <span className="font-medium">{d.comment_count}</span>
            </div>

            <div className="flex-1 min-w-0">
              {workspaceSlug ? (
                <a
                  href={`/${workspaceSlug}/community/${d.id}`}
                  className="text-[15px] font-medium text-foreground hover:text-primary transition-colors truncate block"
                >
                  {d.title}
                </a>
              ) : (
                <p className="text-[15px] font-medium text-foreground truncate">{d.title}</p>
              )}

              <p className="text-[12px] text-muted-foreground mt-2 line-clamp-2">{d.body}</p>

              <div className="flex items-center gap-3 mt-3 text-[11px] text-muted-foreground">
                {d.tags.length > 0 && (
                  <span className="flex gap-1.5">
                    {d.tags.slice(0, 3).map(t => (
                      <span key={t.id} className="bg-muted px-1.5 py-0.5 rounded text-[10px]">
                        {t.name}
                      </span>
                    ))}
                  </span>
                )}
                <span>{d.upvote_count - d.downvote_count} votes</span>
                <span>{formatRelativeTime(d.created_at)}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
