'use client';

import { useState, useEffect } from 'react';
import { ArrowBigUp, ArrowBigDown } from 'lucide-react';
import { useVoteDiscussion, useRemoveVote } from '@/lib/hooks/use-community';

interface UpvoteButtonProps {
  discussionId: string;
  upvoteCount: number;
  userVote: number | null;
}

export function UpvoteButton({ discussionId, upvoteCount, userVote }: UpvoteButtonProps) {
  const voteMutation = useVoteDiscussion(discussionId);
  const removeVoteMutation = useRemoveVote(discussionId);
  const isPending = voteMutation.isPending || removeVoteMutation.isPending;
  const [animateCount, setAnimateCount] = useState(false);

  useEffect(() => {
    setAnimateCount(true);
    const id = setTimeout(() => setAnimateCount(false), 200);
    return () => clearTimeout(id);
  }, [upvoteCount]);

  const handleVote = (e: React.MouseEvent, value: 1 | -1) => {
    e.stopPropagation();
    if (isPending) return;
    if (userVote === value) {
      removeVoteMutation.mutate();
    } else {
      voteMutation.mutate(value);
    }
  };

  return (
    <div className="flex flex-col items-center gap-1 shrink-0 text-muted-foreground">
      <button
        onClick={e => handleVote(e, 1)}
        disabled={isPending}
        className={`rounded p-1 transition-colors active:scale-80 ${
          userVote === 1
            ? 'text-primary hover:bg-primary/20'
            : 'hover:text-primary hover:bg-primary/10'
        } ${isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <ArrowBigUp className="w-5 h-5" />
      </button>
      <span
        className={`text-[12px] font-medium transition-transform duration-200 ${
          animateCount ? 'scale-110' : 'scale-100'
        } ${
          userVote === 1 ? 'text-primary' : userVote === -1 ? 'text-destructive' : 'text-foreground'
        }`}
      >
        {upvoteCount}
      </span>
      <button
        onClick={e => handleVote(e, -1)}
        disabled={isPending}
        className={`rounded p-1 transition-colors active:scale-80 ${
          userVote === -1
            ? 'text-destructive hover:bg-destructive/20'
            : 'hover:text-destructive hover:bg-destructive/10'
        } ${isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <ArrowBigDown className="w-5 h-5" />
      </button>
    </div>
  );
}
