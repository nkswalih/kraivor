'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useComments, useCreateComment, useReplies, useVoteComment, useRemoveCommentVote } from '@/lib/hooks/use-community';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useMyProfile } from '@/lib/hooks/use-profiles';
import { Avatar } from '@/components/profiles/avatar';
import { MessageSquare, ChevronDown, ChevronRight, ThumbsUp, ThumbsDown, Reply, X } from 'lucide-react';
import Link from 'next/link';

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

function CommentVote({ discussionId, comment }: { discussionId: string; comment: { id: string; upvote_count: number; downvote_count: number; user_vote: number | null } }) {
  const voteMutation = useVoteComment(discussionId, comment.id);
  const removeMutation = useRemoveCommentVote(discussionId, comment.id);
  const isPending = voteMutation.isPending || removeMutation.isPending;
  const netScore = comment.upvote_count - comment.downvote_count;

  const handleVote = (value: 1 | -1) => {
    if (isPending) return;
    if (comment.user_vote === value) {
      removeMutation.mutate();
    } else {
      voteMutation.mutate(value);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => handleVote(1)}
        disabled={isPending}
        className={`p-1 rounded transition-colors ${
          comment.user_vote === 1
            ? 'text-primary hover:bg-primary/20'
            : 'text-muted-foreground hover:text-primary hover:bg-primary/10'
        } ${isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <ThumbsUp className="w-3.5 h-3.5" />
      </button>
      <span className={`text-[11px] font-medium min-w-[16px] text-center ${
        comment.user_vote === 1 ? 'text-primary' : comment.user_vote === -1 ? 'text-destructive' : 'text-muted-foreground'
      }`}>
        {netScore}
      </span>
      <button
        onClick={() => handleVote(-1)}
        disabled={isPending}
        className={`p-1 rounded transition-colors ${
          comment.user_vote === -1
            ? 'text-destructive hover:bg-destructive/20'
            : 'text-muted-foreground hover:text-destructive hover:bg-destructive/10'
        } ${isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <ThumbsDown className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function ReplyForm({ discussionId, parentId, authorUsername, onDone }: { discussionId: string; parentId: string; authorUsername?: string; onDone: () => void }) {
  const createMutation = useCreateComment(discussionId);
  const [body, setBody] = useState(authorUsername ? `@${authorUsername} ` : '');
  const user = useAuthStore((s) => s.user);
  const { data: myProfile } = useMyProfile();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;
    await createMutation.mutateAsync({
      body: body.trim(),
      parent_id: parentId,
      author_username: user?.email?.split('@')[0] ?? 'anonymous',
      author_display_name: user?.name ?? user?.email?.split('@')[0] ?? 'Anonymous',
      author_avatar_url: myProfile?.avatar_url ?? user?.avatar_url ?? '',
    });
    setBody('');
    onDone();
  };

  return (
    <form onSubmit={handleSubmit} className="mt-2 flex gap-2">
      <textarea
        ref={textareaRef}
        placeholder="Write a reply..."
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={2}
        className="flex-1 bg-background border border-border rounded-md px-2.5 py-1.5 text-[12px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary resize-none"
      />
      <div className="flex flex-col gap-1">
        <button
          type="submit"
          disabled={createMutation.isPending || !body.trim()}
          className="btn-shimmer text-primary-foreground text-[11px] font-medium px-2.5 py-1 rounded-md disabled:opacity-50"
        >
          {createMutation.isPending ? '...' : 'Reply'}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="text-[11px] text-muted-foreground hover:text-foreground px-2.5 py-1"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </form>
  );
}

const MAX_REPLY_DEPTH = 3;

function ReplyList({ discussionId, commentId, depth = 0 }: { discussionId: string; commentId: string; depth?: number }) {
  const { data: replies } = useReplies(discussionId, commentId);
  const [showReplies, setShowReplies] = useState(false);

  if (!replies?.length && !showReplies) return null;

  return (
    <div className={`${depth > 0 ? 'ml-6' : 'ml-8'} mt-2`}>
      {replies && replies.length > 0 && (
        <button
          onClick={() => setShowReplies(!showReplies)}
          className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground mb-1"
        >
          {showReplies ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
        </button>
      )}

      {showReplies && replies && (
        <div className="space-y-2">
          {replies.map((reply) => (
            <CommentItem
              key={reply.id}
              discussionId={discussionId}
              comment={reply}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CommentItem({ discussionId, comment, depth = 0 }: { discussionId: string; comment: any; depth?: number }) {
  const [showReplyForm, setShowReplyForm] = useState(false);
  const isAuthenticated = useAuthStore((s) => !!s.accessToken);
  const params = useParams();
  const workspace = params?.workspace as string;

  return (
    <div className={`${depth > 0 ? 'border-l-2 border-border pl-3' : ''} py-2`}>
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground mb-1">
        <Avatar src={comment.author_avatar_url} name={comment.author_display_name} size="sm" />
        <Link href={`/${workspace}/profile/${comment.author_username}`} className="font-medium text-foreground hover:underline">
          {comment.author_display_name}
        </Link>
        <span>·</span>
        <span>{timeAgo(comment.created_at)}</span>
      </div>
      <div className="text-[13px] text-foreground whitespace-pre-wrap mb-1.5">
        {comment.body}
      </div>
      <div className="flex items-center gap-3">
        <CommentVote discussionId={discussionId} comment={comment} />
        {isAuthenticated && (
          <button
            onClick={() => setShowReplyForm(!showReplyForm)}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          >
            <Reply className="w-3 h-3" />
            Reply
          </button>
        )}
      </div>
      {showReplyForm && (
        <ReplyForm
          discussionId={discussionId}
          parentId={comment.id}
          authorUsername={comment.author_username}
          onDone={() => setShowReplyForm(false)}
        />
      )}
      {comment.reply_count > 0 && depth < MAX_REPLY_DEPTH && (
        <ReplyList discussionId={discussionId} commentId={comment.id} depth={depth} />
      )}
    </div>
  );
}

interface CommentsSectionProps {
  discussionId: string;
}

export function CommentsSection({ discussionId }: CommentsSectionProps) {
  const [sort, setSort] = useState<'newest' | 'top'>('newest');
  const { data, isLoading } = useComments(discussionId, { sort });
  const createMutation = useCreateComment(discussionId);
  const [body, setBody] = useState('');
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => !!s.accessToken);
  const { data: myProfile } = useMyProfile();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;
    await createMutation.mutateAsync({
      body: body.trim(),
      author_username: myProfile?.username ?? user?.email?.split('@')[0] ?? 'anonymous',
      author_display_name: myProfile?.display_name ?? user?.name ?? user?.email?.split('@')[0] ?? 'Anonymous',
      author_avatar_url: myProfile?.avatar_url ?? user?.avatar_url ?? '',
    });
    setBody('');
  };

  return (
    <div className="border-t border-border pt-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          Comments ({data?.total ?? 0})
        </h3>
        <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
          <button
            onClick={() => setSort('newest')}
            className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition-colors ${
              sort === 'newest' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Newest
          </button>
          <button
            onClick={() => setSort('top')}
            className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition-colors ${
              sort === 'top' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Top
          </button>
        </div>
      </div>

      {isAuthenticated ? (
        <form onSubmit={handleSubmit} className="mb-6">
          <textarea
            placeholder="Add a comment..."
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary resize-none"
            required
          />
          <div className="flex justify-end mt-2">
            <button
              type="submit"
              disabled={createMutation.isPending || !body.trim()}
              className="btn-shimmer text-primary-foreground text-[13px] font-medium px-4 py-1.5 rounded-md disabled:opacity-50"
            >
              {createMutation.isPending ? 'Posting...' : 'Comment'}
            </button>
          </div>
        </form>
      ) : (
        <div className="text-[13px] text-muted-foreground mb-6">
          <Link href="/auth/signin" className="text-primary hover:underline">Sign in</Link> to leave a comment.
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-3 bg-muted rounded w-1/4 mb-2" />
              <div className="h-8 bg-muted rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {data?.results.map((comment) => (
            <CommentItem
              key={comment.id}
              discussionId={discussionId}
              comment={comment}
            />
          ))}
          {data?.results.length === 0 && (
            <p className="text-[13px] text-muted-foreground text-center py-8">
              No comments yet. Be the first to share your thoughts!
            </p>
          )}
        </div>
      )}
    </div>
  );
}
