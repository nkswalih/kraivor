'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useProfile, useFollowers, useFollowing } from '@/lib/hooks/use-profiles';
import { ProfileHeader } from '@/components/profiles/profile-header';
import { Avatar } from '@/components/profiles/avatar';
import { Skeleton } from '@/components/ui/shadcn';
import { formatRelativeTime } from '@/lib/utils';
import { cn } from '@/lib/utils';

type Tab = 'discussions' | 'comments' | 'followers' | 'following';

export default function UserProfilePage() {
  const params = useParams();
  const router = useRouter();
  const username = params?.slug as string;
  const { data: profile, isLoading, error } = useProfile(username);
  const [activeTab, setActiveTab] = useState<Tab>('followers');

  const { data: followersData, isLoading: followersLoading } = useFollowers(username);
  const { data: followingData, isLoading: followingLoading } = useFollowing(username);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto p-6 w-full animate-pulse space-y-4">
        <div className="h-32 bg-muted rounded-lg" />
        <div className="h-16 w-16 bg-muted rounded-full -mt-12 ml-6" />
        <div className="h-6 bg-muted rounded w-1/4 ml-6" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="max-w-3xl mx-auto p-6 w-full text-center text-muted-foreground">
        Profile not found.
      </div>
    );
  }

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: 'discussions', label: 'Discussions', count: profile.discussion_count },
    { key: 'comments', label: 'Comments', count: profile.comment_count },
    { key: 'followers', label: 'Followers', count: profile.followers_count },
    { key: 'following', label: 'Following', count: profile.following_count },
  ];

  const workspace = params?.workspace as string;
  const followers = followersData?.results ?? [];
  const following = followingData?.results ?? [];

  return (
    <div className="max-w-3xl mx-auto p-6 w-full">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>
      <ProfileHeader profile={profile} userAvatarUrl={profile.user_avatar_url} />

      {/* Tabs */}
      <div className="flex border-b border-border mt-6">
        {tabs.map((tab) => (
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
            {tab.label}{' '}
            <span className="text-muted-foreground">({tab.count})</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="mt-4">
        {activeTab === 'discussions' && (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-[13px]">Discussion history coming soon</p>
          </div>
        )}

        {activeTab === 'comments' && (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-[13px]">Comment history coming soon</p>
          </div>
        )}

        {activeTab === 'followers' && (
          <div className="space-y-2">
            {followersLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-12 w-full rounded-md" />
                ))}
              </div>
            ) : followers.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <p className="text-[13px]">No followers yet</p>
              </div>
            ) : (
              followers.map((f) => (
                <Link
                  key={f.id}
                  href={`/${workspace}/profile/${f.username}`}
                  className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-accent transition-colors"
                >
                  <Avatar src={f.avatar_url} fallbackSrc={f.user_avatar_url} name={f.display_name} size="md" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-foreground truncate">
                      {f.display_name}
                    </p>
                    <p className="text-[12px] text-muted-foreground truncate">
                      @{f.username}
                    </p>
                  </div>
                  <p className="text-[11px] text-muted-foreground shrink-0">
                    Followed {formatRelativeTime(f.followed_at)}
                  </p>
                </Link>
              ))
            )}
          </div>
        )}

        {activeTab === 'following' && (
          <div className="space-y-2">
            {followingLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-12 w-full rounded-md" />
                ))}
              </div>
            ) : following.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <p className="text-[13px]">Not following anyone yet</p>
              </div>
            ) : (
              following.map((f) => (
                <Link
                  key={f.id}
                  href={`/${workspace}/profile/${f.username}`}
                  className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-accent transition-colors"
                >
                  <Avatar src={f.avatar_url} fallbackSrc={f.user_avatar_url} name={f.display_name} size="md" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-foreground truncate">
                      {f.display_name}
                    </p>
                    <p className="text-[12px] text-muted-foreground truncate">
                      @{f.username}
                    </p>
                  </div>
                  <p className="text-[11px] text-muted-foreground shrink-0">
                    Followed {formatRelativeTime(f.followed_at)}
                  </p>
                </Link>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
