'use client';

import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Avatar } from './avatar';
import { FollowButton } from './follow-button';
import type { Profile } from '@/types/domain/profiles';
import {
  MapPin,
  Link as LinkIcon,
  Github,
  Twitter,
  Linkedin,
  Pencil,
  Share2,
  MessageSquare,
} from 'lucide-react';
import { copyToClipboard } from '@/lib/utils';

interface ProfileHeaderProps {
  profile: Profile;
  userAvatarUrl?: string;
}

export function ProfileHeader({ profile, userAvatarUrl }: ProfileHeaderProps) {
  const router = useRouter();

  const handleShare = async () => {
    const url = `${window.location.origin}/profile/${profile.username}`;
    const copied = await copyToClipboard(url);
    if (copied) {
      toast.success('Profile link copied to clipboard');
    } else {
      toast.error('Failed to copy link');
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Banner */}
      <div className="h-32 bg-gradient-to-r from-primary/20 via-primary/10 to-background">
        {profile.banner_url && (
          <img src={profile.banner_url} alt="" className="w-full h-full object-cover" />
        )}
      </div>

      {/* Avatar & Info */}
      <div className="px-6 pb-6">
        <div className="-mt-12 mb-4">
          <Avatar
            src={profile.avatar_url}
            fallbackSrc={userAvatarUrl}
            name={profile.display_name}
            size="xl"
          />
        </div>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-medium text-foreground">{profile.display_name}</h1>
            <p className="text-[13px] text-muted-foreground">@{profile.username}</p>
          </div>
          <div className="flex items-center gap-2">
            {profile.is_owner && (
              <button
                onClick={() => router.push(`/profile/${profile.username}/edit`)}
                className="flex items-center gap-1.5 text-[12px] font-medium text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-md border border-border hover:bg-accent transition-colors"
              >
                <Pencil className="w-3.5 h-3.5" />
                Edit Profile
              </button>
            )}
            <button
              onClick={handleShare}
              className="flex items-center gap-1.5 text-[12px] font-medium text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-md border border-border hover:bg-accent transition-colors"
            >
              <Share2 className="w-3.5 h-3.5" />
              Share
            </button>
            <FollowButton
              username={profile.username}
              isFollowing={profile.is_following}
              isOwner={profile.is_owner}
            />
          </div>
        </div>

        {profile.bio && <p className="text-[13px] text-foreground mt-3 max-w-lg">{profile.bio}</p>}

        <div className="flex items-center gap-4 mt-3 text-[12px] text-muted-foreground flex-wrap">
          {profile.location && (
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" /> {profile.location}
            </span>
          )}
          {profile.website_url && (
            <a
              href={profile.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-foreground"
            >
              <LinkIcon className="w-3.5 h-3.5" /> Website
            </a>
          )}
          {profile.github_username && (
            <a
              href={`https://github.com/${profile.github_username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-foreground"
            >
              <Github className="w-3.5 h-3.5" /> {profile.github_username}
            </a>
          )}
          {profile.twitter_username && (
            <a
              href={`https://twitter.com/${profile.twitter_username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-foreground"
            >
              <Twitter className="w-3.5 h-3.5" /> @{profile.twitter_username}
            </a>
          )}
          {profile.linkedin_url && (
            <a
              href={profile.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-foreground"
            >
              <Linkedin className="w-3.5 h-3.5" /> LinkedIn
            </a>
          )}
        </div>

        <ProfileStats
          reputation={profile.reputation_score}
          followers={profile.followers_count}
          following={profile.following_count}
          discussions={profile.discussion_count}
          comments={profile.comment_count}
        />
      </div>
    </div>
  );
}

function ProfileStats({
  reputation,
  followers,
  following,
  discussions,
  comments,
}: {
  reputation: number;
  followers: number;
  following: number;
  discussions: number;
  comments: number;
}) {
  const stats = [
    { label: 'Reputation', value: reputation.toLocaleString() },
    { label: 'Followers', value: followers.toLocaleString() },
    { label: 'Following', value: following.toLocaleString() },
    { label: 'Discussions', value: discussions.toLocaleString() },
    { label: 'Comments', value: comments.toLocaleString() },
  ];

  return (
    <div className="flex items-center gap-6 mt-4 pt-4 border-t border-border">
      {stats.map(stat => (
        <div key={stat.label} className="text-center">
          <div className="text-sm font-medium text-foreground">{stat.value}</div>
          <div className="text-[11px] text-muted-foreground">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
