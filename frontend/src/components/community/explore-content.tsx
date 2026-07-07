'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Search, Users, MessageSquare } from 'lucide-react';
import { useDiscussions } from '@/lib/hooks/use-community';
import { useProfileSearch } from '@/lib/hooks/use-profiles';
import { useAuthorProfiles } from '@/lib/hooks/use-profiles';
import { useCommunityStore } from '@/lib/stores/community-store';
import { DiscussionCard } from './discussion-card';
import { Avatar } from '@/components/profiles/avatar';

export function ExploreContent() {
  const router = useRouter();
  const params = useParams();
  const workspace = params?.workspace as string;
  const searchQuery = useCommunityStore(s => s.searchQuery);
  const [debounced, setDebounced] = useState('');

  useEffect(() => {
    const id = setTimeout(() => setDebounced(searchQuery), 200);
    return () => clearTimeout(id);
  }, [searchQuery]);

  const { data: profileData, isLoading: profilesLoading } = useProfileSearch(debounced);
  const { data: discussionData, isLoading: discussionsLoading } = useDiscussions({
    sort: 'latest',
    search: debounced || undefined,
  });

  const profileResults = profileData?.results ?? [];
  const discussionResults = discussionData?.results ?? [];
  const hasQuery = debounced.length > 0;

  const authorIds = useMemo(
    () => [...new Set(discussionResults.map(d => d.author_id))],
    [discussionResults]
  );
  const { data: resolvedData } = useAuthorProfiles(authorIds);
  const profileMap = resolvedData?.profileMap ?? {};

  if (!hasQuery) {
    if (discussionsLoading) {
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
    if (!discussionResults.length) {
      return (
        <div className="text-center py-16">
          <Search className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
          <h3 className="text-[15px] font-medium text-foreground mb-1">Explore discussions & people</h3>
          <p className="text-[13px] text-muted-foreground">
            Search for discussions, topics, or people in the community.
          </p>
        </div>
      );
    }
    return (
      <div className="space-y-4">
        {discussionResults.map(discussion => (
          <DiscussionCard
            key={discussion.id}
            discussion={discussion}
            resolvedAuthor={profileMap[discussion.author_id] ?? null}
          />
        ))}
      </div>
    );
  }

  const loading = profilesLoading || discussionsLoading;

  if (loading) {
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

  const noResults = profileResults.length === 0 && discussionResults.length === 0;

  if (noResults) {
    return (
      <div className="text-center py-16">
        <Search className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
        <h3 className="text-[15px] font-medium text-foreground mb-1">No results for "{debounced}"</h3>
        <p className="text-[13px] text-muted-foreground">
          Try different keywords or check the spelling.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {profileResults.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-[13px] font-semibold text-muted-foreground uppercase tracking-wider">
              People
            </h3>
          </div>
          <div className="space-y-1">
            {profileResults.slice(0, 5).map(profile => (
              <button
                key={profile.user_id}
                onClick={() => router.push(`/${workspace}/profile/${profile.username}`)}
                className="flex items-center gap-3 w-full p-2.5 rounded-lg hover:bg-muted/50 transition-colors text-left"
              >
                <Avatar
                  src={profile.avatar_url}
                  fallbackSrc={profile.user_avatar_url}
                  name={profile.display_name}
                  size="sm"
                />
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium text-foreground truncate">
                    {profile.display_name}
                  </div>
                  <div className="text-[12px] text-muted-foreground">
                    @{profile.username} · {profile.reputation_score} rep
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {discussionResults.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-[13px] font-semibold text-muted-foreground uppercase tracking-wider">
              Discussions
            </h3>
          </div>
          <div className="space-y-4">
            {discussionResults.map(discussion => (
              <DiscussionCard
                key={discussion.id}
                discussion={discussion}
                resolvedAuthor={profileMap[discussion.author_id] ?? null}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
