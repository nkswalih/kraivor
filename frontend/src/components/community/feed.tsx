'use client';

import { useDiscussions } from '@/lib/hooks/use-community';
import { useCommunityStore } from '@/lib/stores/community-store';
import { DiscussionCard } from './discussion-card';

export function Feed() {
  const activeSort = useCommunityStore((s) => s.activeSort);
  const activeTag = useCommunityStore((s) => s.activeTag);
  const { data, isLoading, error } = useDiscussions({
    sort: activeSort,
    tag: activeTag ?? undefined,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-card border border-border rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-muted rounded w-3/4 mb-3" />
            <div className="h-3 bg-muted rounded w-1/2 mb-2" />
            <div className="h-3 bg-muted rounded w-1/4" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Failed to load discussions. Please try again.
      </div>
    );
  }

  if (!data?.results.length) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No discussions yet. Start one!
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {data.results.map((discussion) => (
        <DiscussionCard key={discussion.id} discussion={discussion} />
      ))}
    </div>
  );
}
