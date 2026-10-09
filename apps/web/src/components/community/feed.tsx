'use client';

import { useMemo } from 'react';
import { useDiscussions } from '@/lib/hooks/use-community';
import { useCommunityStore, defaultSort } from '@/lib/stores/community-store';
import { useAuthorProfiles } from '@/lib/hooks/use-profiles';
import { DiscussionCard } from './discussion-card';
import { Skeleton } from '@/components/ui/shadcn';

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
          <div key={i} className="bg-card border border-border rounded-lg p-4">
            <div className="flex gap-4">
              <Skeleton variant="rect" className="w-10 h-10 shrink-0" />
              <div className="flex-1 min-w-0 space-y-3">
                <div className="flex items-center gap-2">
                  <Skeleton variant="circle" className="w-5 h-5" />
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-3 w-12" />
                </div>
                <Skeleton className="h-5 w-3/4" />
                <div className="flex gap-2">
                  <Skeleton className="h-5 w-14 rounded-full" />
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
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
