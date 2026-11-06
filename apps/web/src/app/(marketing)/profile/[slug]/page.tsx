'use client';

import { useParams } from 'next/navigation';
import { useProfile } from '@/lib/hooks/use-profiles';
import { ProfileView } from '@/components/profiles/profile-view';

/**
 * The public profile. Same `ProfileView` the workspace renders, minus the two
 * workspace-only props: no slug means `/profile/{username}` links, and no
 * `onOpenProfile` means people here navigate, because this layout has no card
 * to open. The page scrolls with the document -- the marketing shell is not
 * `overflow-hidden` the way the dashboard is.
 */
export default function UserProfilePage() {
  const params = useParams();
  const username = params?.slug as string;
  const { data: profile, isLoading, error } = useProfile(username);

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

  return (
    <div className="max-w-3xl mx-auto p-6 w-full">
      <ProfileView profile={profile} />
    </div>
  );
}
