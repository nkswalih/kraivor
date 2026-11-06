'use client';

import { useParams } from 'next/navigation';
import { useProfile } from '@/lib/hooks/use-profiles';
import { useProfileDialogStore } from '@/lib/stores/profile-dialog-store';
import { ProfileView } from '@/components/profiles/profile-view';

/**
 * The full-page profile, kept for pasted and shared URLs.
 *
 * In-app visits open the card (`ProfileDialog`) instead of coming here, so
 * this route no longer sets the breadcrumb -- the topbar keeps showing the
 * page you were actually on -- and it scrolls on its own, because the
 * dashboard's `main` is `overflow-hidden` and every page owns its own
 * scrollbar.
 */
export default function UserProfilePage() {
  const params = useParams();
  const username = params?.slug as string;
  const workspace = params?.workspace as string;
  const openProfile = useProfileDialogStore(s => s.open);
  const { data: profile, isLoading, error } = useProfile(username);

  if (isLoading) {
    return (
      <div className="flex-1 min-h-0 overflow-y-auto w-full">
        <div className="max-w-3xl mx-auto p-6 w-full animate-pulse space-y-4">
          <div className="h-32 bg-muted rounded-lg" />
          <div className="h-16 w-16 bg-muted rounded-full -mt-12 ml-6" />
          <div className="h-6 bg-muted rounded w-1/4 ml-6" />
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="flex-1 min-h-0 overflow-y-auto w-full">
        <div className="max-w-3xl mx-auto p-6 w-full text-center text-muted-foreground">
          Profile not found.
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto w-full">
      <div className="max-w-3xl mx-auto p-6 w-full">
        <ProfileView
          profile={profile}
          workspaceSlug={workspace}
          onOpenProfile={openProfile}
        />
      </div>
    </div>
  );
}
