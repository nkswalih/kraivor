'use client';

import { useEffect, useState } from 'react';
import { useFollowers, useFollowing } from '@/lib/hooks/use-profiles';
import { ProfileHeader } from './profile-header';
import { UserDiscussionList } from './user-discussions-list';
import { UserCommentList } from './user-comments-list';
import { UserRow } from '@/components/users/user-row';
import { Skeleton } from '@/components/ui/shadcn';
import { cn, formatRelativeTime } from '@/lib/utils';
import { profileHref } from './profile-link';
import type { Profile } from '@/types/domain/profiles';

type Tab = 'discussions' | 'comments' | 'followers' | 'following';

interface ProfileViewProps {
  profile: Profile;
  /** Omitted on the public marketing profile (no workspace context). */
  workspaceSlug?: string;
  /**
   * Open the profile card rather than navigating. Passed by every surface that
   * has the dialog mounted; the public profile page omits it and falls back to
   * plain links.
   */
  onOpenProfile?: (username: string) => void;
}

/**
 * The profile itself: header card, the four tabs, and their lists.
 *
 * Extracted so the full-page route (pasted URLs) and the dialog render one
 * component instead of two copies that drift -- they differ only in whether a
 * click on a person opens the card, which is a prop rather than a fork.
 */
export function ProfileView({ profile, workspaceSlug, onOpenProfile }: ProfileViewProps) {
  const username = profile.username;
  const [activeTab, setActiveTab] = useState<Tab>('followers');

  const {
    data: followersData,
    isLoading: followersLoading,
    refetch: refetchFollowers,
  } = useFollowers(username);
  const {
    data: followingData,
    isLoading: followingLoading,
    refetch: refetchFollowing,
  } = useFollowing(username);

  useEffect(() => {
    if (activeTab === 'followers') refetchFollowers();
    if (activeTab === 'following') refetchFollowing();
  }, [activeTab, refetchFollowers, refetchFollowing]);

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: 'discussions', label: 'Discussions', count: profile.discussion_count },
    { key: 'comments', label: 'Comments', count: profile.comment_count },
    { key: 'followers', label: 'Followers', count: profile.followers_count },
    { key: 'following', label: 'Following', count: profile.following_count },
  ];

  const followers = followersData?.results ?? [];
  const following = followingData?.results ?? [];

  const renderRows = (
    people: typeof followers,
    loading: boolean,
    empty: string
  ) => (
    <div className="space-y-2">
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <Skeleton key={i} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : people.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p className="text-[13px]">{empty}</p>
        </div>
      ) : (
        people.map(f => (
          <UserRow
            key={f.id}
            variant="detail"
            href={profileHref(f.username, workspaceSlug)}
            name={f.display_name}
            username={f.username}
            avatarUrl={f.avatar_url}
            fallbackAvatarUrl={f.user_avatar_url}
            onOpenProfile={
              onOpenProfile ? () => onOpenProfile(f.username) : undefined
            }
            trailing={
              <span className="text-[11px] text-muted-foreground">
                Followed {formatRelativeTime(f.followed_at)}
              </span>
            }
          />
        ))
      )}
    </div>
  );

  return (
    <div>
      <ProfileHeader
        profile={profile}
        userAvatarUrl={profile.user_avatar_url}
        workspaceSlug={workspaceSlug}
      />

      {/* Tabs */}
      <div className="flex border-b border-border mt-6">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-4 py-2.5 text-[13px] font-medium border-b-2 transition-colors -mb-px',
              activeTab === tab.key
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label} <span className="text-muted-foreground">({tab.count})</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="mt-4">
        {activeTab === 'discussions' && (
          <UserDiscussionList userId={profile.user_id} workspaceSlug={workspaceSlug} />
        )}

        {activeTab === 'comments' && (
          <UserCommentList userId={profile.user_id} workspaceSlug={workspaceSlug} />
        )}

        {activeTab === 'followers' &&
          renderRows(followers, followersLoading, 'No followers yet')}

        {activeTab === 'following' &&
          renderRows(following, followingLoading, 'Not following anyone yet')}
      </div>
    </div>
  );
}
