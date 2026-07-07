'use client';

import { useMemo } from 'react';
import { useDiscussions } from '@/lib/hooks/use-community';
import { useCommunityStore, defaultSort } from '@/lib/stores/community-store';
import { useAuthorProfiles } from '@/lib/hooks/use-profiles';
import { DiscussionCard } from './discussion-card';

export function Feed() {
  const activeTab = useCommunityStore(s => s.activeTab);
  const sortOption = useCommunityStore(s => s.sortOption);
  const activeTag = useCommunityStore(s => s.activeTag);
  const searchQuery = useCommunityStore(s => s.searchQuery);
  const viewMode = useCommunityStore(s => s.viewMode);

  const sort = sortOption ?? defaultSort(activeTab);
  const tag = activeTab === 'news'
    ? 'news'
    : activeTag ?? undefined;

  const { data, isLoading, error } = useDiscussions({
    sort,
    tag,
    search: activeTab === 'explore' ? searchQuery || undefined : undefined,
  });

  const authorIds = useMemo(
    () => [...new Set((data?.results ?? []).map(d => d.author_id))],
    [data?.results]
  );
  const { data: resolvedData } = useAuthorProfiles(authorIds);
  const profileMap = resolvedData?.profileMap ?? {};

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map(i => (
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
    const msg = activeTab === 'explore' && searchQuery
      ? `No discussions match "${searchQuery}".`
      : activeTab === 'news'
      ? 'No news discussions yet.'
      : 'No discussions yet. Start one!';
    return (
      <div className="text-center py-8 text-muted-foreground">{msg}</div>
    );
  }

  if (viewMode === 'grid') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.results.map(discussion => (
          <DiscussionCard
            key={discussion.id}
            discussion={discussion}
            resolvedAuthor={profileMap[discussion.author_id] ?? null}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {data.results.map(discussion => (
        <DiscussionCard
          key={discussion.id}
          discussion={discussion}
          resolvedAuthor={profileMap[discussion.author_id] ?? null}
        />
      ))}
    </div>
  );
}
