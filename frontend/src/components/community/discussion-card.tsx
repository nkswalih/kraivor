'use client';

import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { MessageSquare, Share2 } from 'lucide-react';
import { toast } from 'sonner';
import { TagChip } from './tag-chip';
import { UpvoteButton } from './upvote-button';
import { Avatar } from '@/components/profiles/avatar';
import { copyToClipboard } from '@/lib/utils';
import type { Discussion } from '@/types/domain/community';

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

interface DiscussionCardProps {
  discussion: Discussion;
}

export function DiscussionCard({ discussion }: DiscussionCardProps) {
  const router = useRouter();
  const params = useParams();
  const workspace = params?.workspace as string;

  const handleShare = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const url = `${window.location.origin}/${workspace}/community/${discussion.id}`;
    const ok = await copyToClipboard(url);
    if (ok) {
      toast.success('Link copied to clipboard');
    } else {
      toast.error('Failed to copy link');
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/${workspace}/community/${discussion.id}`)}
      onKeyDown={e => {
        if (e.key === 'Enter') router.push(`/${workspace}/community/${discussion.id}`);
      }}
      className="block bg-card border border-border rounded-lg p-4 hover:border-primary/40 transition-colors cursor-pointer group"
    >
      <div className="flex gap-4">
        <UpvoteButton
          discussionId={discussion.id}
          upvoteCount={discussion.upvote_count - discussion.downvote_count}
          userVote={discussion.user_vote}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground mb-1.5">
            <Avatar
              src={discussion.author_avatar_url}
              name={discussion.author_display_name}
              size="sm"
            />
            <Link
              href={`/${workspace}/profile/${discussion.author_username}`}
              onClick={e => e.stopPropagation()}
              className="font-medium text-foreground hover:underline"
            >
              {discussion.author_display_name}
            </Link>
            <span>·</span>
            <span>{timeAgo(discussion.created_at)}</span>
          </div>

          <h3 className="text-[15px] font-medium text-foreground mb-2 group-hover:text-primary transition-colors truncate">
            {discussion.title}
          </h3>

          {discussion.tags.length > 0 && (
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              {discussion.tags.map(tag => (
                <TagChip key={tag.id} name={tag.name} slug={tag.slug} />
              ))}
            </div>
          )}

          <div className="flex items-center gap-4 text-muted-foreground text-[12px]">
            <span className="flex items-center gap-1.5 hover:text-foreground transition-colors">
              <MessageSquare className="w-4 h-4" /> {discussion.comment_count}
            </span>
            <button
              onClick={handleShare}
              className="flex items-center gap-1.5 hover:text-foreground transition-colors"
            >
              <Share2 className="w-4 h-4" /> Share
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
