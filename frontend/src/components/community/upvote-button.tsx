'use client';

import { ArrowBigUp, ArrowBigDown } from 'lucide-react';
import { motion } from 'framer-motion';
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

  const handleVote = (value: 1 | -1) => {
    if (isPending) return;
    if (userVote === value) {
      removeVoteMutation.mutate();
    } else {
      voteMutation.mutate(value);
    }
  };

  return (
    <div className="flex flex-col items-center gap-1 shrink-0 text-muted-foreground">
      <motion.button
        whileTap={{ scale: 0.8 }}
        onClick={() => handleVote(1)}
        disabled={isPending}
        className={`rounded p-1 transition-colors ${
          userVote === 1
            ? 'text-primary hover:bg-primary/20'
            : 'hover:text-primary hover:bg-primary/10'
        } ${isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <ArrowBigUp className="w-5 h-5" />
      </motion.button>
      <motion.span
        key={upvoteCount}
        initial={{ scale: 1.2 }}
        animate={{ scale: 1 }}
        className={`text-[12px] font-medium ${
          userVote === 1 ? 'text-primary' : userVote === -1 ? 'text-destructive' : 'text-foreground'
        }`}
      >
        {upvoteCount}
      </motion.span>
      <motion.button
        whileTap={{ scale: 0.8 }}
        onClick={() => handleVote(-1)}
        disabled={isPending}
        className={`rounded p-1 transition-colors ${
          userVote === -1
            ? 'text-destructive hover:bg-destructive/20'
            : 'hover:text-destructive hover:bg-destructive/10'
        } ${isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <ArrowBigDown className="w-5 h-5" />
      </motion.button>
    </div>
  );
}
