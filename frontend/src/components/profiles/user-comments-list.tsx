'use client';

import { useUserComments } from '@/lib/hooks/use-profiles';
import { MessageCircle, ThumbsUp } from 'lucide-react';
import { Skeleton } from '@/components/ui/shadcn';
import { formatRelativeTime } from '@/lib/utils';

interface UserCommentListProps {
  userId: string;
  workspaceSlug?: string;
}

export function UserCommentList({ userId, workspaceSlug }: UserCommentListProps) {
  const { data, isLoading } = useUserComments(userId);
  const comments = data?.results ?? [];

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (comments.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <MessageCircle className="w-8 h-8 mx-auto mb-3 opacity-40" />
        <p className="text-[13px]">No comments yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {comments.map(c => (
        <div
          key={c.id}
          className="bg-card border border-border rounded-lg p-4 hover:border-primary/40 transition-colors"
        >
          <p className="text-[13px] text-foreground leading-relaxed line-clamp-2">{c.body}</p>

          <div className="flex items-center gap-3 mt-3 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <ThumbsUp className="w-3 h-3" />
              {c.upvote_count - c.downvote_count}
            </span>
            {workspaceSlug && (
              <a
                href={`/${workspaceSlug}/community/${c.discussion_id}`}
                className="hover:text-foreground transition-colors"
              >
                View discussion
              </a>
            )}
            <span>{formatRelativeTime(c.created_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
