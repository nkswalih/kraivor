'use client';

import { useFollow, useUnfollow } from '@/lib/hooks/use-profiles';

interface FollowButtonProps {
  username: string;
  isFollowing: boolean;
  isOwner: boolean;
}

export function FollowButton({ username, isFollowing, isOwner }: FollowButtonProps) {
  const followMutation = useFollow(username);
  const unfollowMutation = useUnfollow(username);

  if (isOwner) return null;

  const handleClick = () => {
    if (isFollowing) {
      unfollowMutation.mutate();
    } else {
      followMutation.mutate();
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={followMutation.isPending || unfollowMutation.isPending}
      className={`text-[13px] font-medium px-4 py-1.5 rounded-md border transition-colors active:scale-95 ${
        isFollowing
          ? 'bg-background border-border text-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/50'
          : 'btn-shimmer text-primary-foreground border-transparent'
      }`}
    >
      {followMutation.isPending || unfollowMutation.isPending
        ? '...'
        : isFollowing
          ? 'Following'
          : 'Follow'}
    </button>
  );
}
