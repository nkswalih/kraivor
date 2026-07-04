'use client';

import { useDiscussion } from '@/lib/hooks/use-community';
import { useDetailBreadcrumb } from '@/lib/hooks/use-detail-breadcrumb';
import { Avatar } from '@/components/profiles/avatar';
import { UpvoteButton } from './upvote-button';
import { TagChip } from './tag-chip';
import { CommentsSection } from './comments';
import { TrendingSidebar } from './trending-sidebar';
import { ShareDialog } from './share-dialog';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

function timeAgo(date: string): string {
  const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(date).toLocaleDateString();
}

interface DiscussionDetailProps {
  discussionId: string;
}

export function DiscussionDetail({ discussionId }: DiscussionDetailProps) {
  const { data: discussion, isLoading, error } = useDiscussion(discussionId);
  useDetailBreadcrumb(discussion?.title);
  const params = useParams();
  const workspace = params?.workspace as string;

  if (isLoading) {
    return (
      <div className="flex h-full w-full">
        <div className="flex-1 overflow-y-auto p-6 max-w-[1000px] mx-auto border-r border-border bg-background">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-muted rounded w-3/4" />
            <div className="h-4 bg-muted rounded w-1/4" />
            <div className="h-32 bg-muted rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !discussion) {
    return <div className="p-6 text-center text-muted-foreground">Discussion not found.</div>;
  }

  return (
    <div className="flex h-full w-full animate-fade-up">
      <div className="flex-1 overflow-y-auto p-6 max-w-[1000px] mx-auto border-r border-border bg-background">
        <Link
          href={`/${workspace}/community`}
          className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to community
        </Link>

        <div className="flex gap-4 mb-8">
          <UpvoteButton
            discussionId={discussion.id}
            upvoteCount={discussion.upvote_count - discussion.downvote_count}
            userVote={discussion.user_vote}
          />

          <div className="flex-1">
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground mb-2">
              <Avatar
                src={discussion.author_avatar_url}
                name={discussion.author_display_name}
                size="sm"
              />
              <Link
                href={`/${discussion.author_username}`}
                className="font-medium text-foreground hover:underline"
              >
                {discussion.author_display_name}
              </Link>
              <span>·</span>
              <span>{timeAgo(discussion.created_at)}</span>
              <span>·</span>
              <span>{discussion.comment_count} comments</span>
            </div>

            <h1 className="text-xl font-medium text-foreground mb-4">{discussion.title}</h1>

            {discussion.tags.length > 0 && (
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                {discussion.tags.map(tag => (
                  <TagChip key={tag.id} name={tag.name} slug={tag.slug} size="md" />
                ))}
              </div>
            )}

            <div className="flex items-center gap-3 text-[12px] text-muted-foreground mb-4">
              <ShareDialog discussionId={discussion.id} title={discussion.title} />
            </div>

            <div className="prose prose-sm dark:prose-invert max-w-none text-foreground mb-8 whitespace-pre-wrap">
              {discussion.body}
            </div>

            {discussion.is_resolved && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/30 text-green-500 text-[12px] font-medium mb-4">
                Resolved
              </div>
            )}

            {discussion.is_locked && (
              <div className="text-[12px] text-muted-foreground mb-4">
                This discussion is locked.
              </div>
            )}
          </div>
        </div>

        <CommentsSection discussionId={discussionId} />
      </div>

      <div className="w-[300px] bg-card p-6 hidden lg:block shrink-0 overflow-y-auto">
        <TrendingSidebar />
      </div>
    </div>
  );
}
