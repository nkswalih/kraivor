'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/shadcn';
import { useProfile } from '@/lib/hooks/use-profiles';
import { useProfileDialogStore } from '@/lib/stores/profile-dialog-store';
import { ProfileView } from './profile-view';

interface ProfileDialogProps {
  workspaceSlug?: string;
}

/**
 * The Discord-style profile card: one big dialog, scrolled inside itself.
 *
 * Mounted once (next to the CommandPalette in the topbar) so it is available
 * on every workspace page -- chat, community, search, the sidebar -- without
 * any of them navigating away. Opening a different person while it is up just
 * swaps the username in the store; there is never a second dialog stacked on
 * the first, and a follower clicked inside the card *becomes* the card.
 *
 * Two lifetimes are deliberate:
 *
 *  - a route change closes it, so Message and Edit Profile can navigate
 *    normally and the card does not float over the page they land on;
 *  - the profile query lives in the inner component, which Radix unmounts with
 *    the content, so a closed dialog never fetches anything.
 */
export function ProfileDialog({ workspaceSlug }: ProfileDialogProps) {
  const username = useProfileDialogStore(s => s.username);
  const close = useProfileDialogStore(s => s.close);
  const openProfile = useProfileDialogStore(s => s.open);
  const pathname = usePathname();

  useEffect(() => {
    close();
  }, [pathname, close]);

  return (
    <Dialog
      open={username !== null}
      onOpenChange={next => {
        if (!next) close();
      }}
    >
      <DialogContent className="max-w-2xl w-[calc(100vw-2rem)] p-0">
        <div className="max-h-[85vh] overflow-y-auto overscroll-contain px-6 py-6">
          {username !== null && (
            <ProfileCardContent
              username={username}
              workspaceSlug={workspaceSlug}
              onOpenProfile={openProfile}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ProfileCardContent({
  username,
  workspaceSlug,
  onOpenProfile,
}: {
  username: string;
  workspaceSlug?: string;
  onOpenProfile: (username: string) => void;
}) {
  const { data: profile, isLoading, error } = useProfile(username);

  return (
    <>
      {/* Radix needs a title for the accessible name of the dialog; it is not
          a visual one -- the banner and name below carry that. */}
      <DialogTitle className="sr-only">{profile?.display_name ?? 'Profile'}</DialogTitle>
      <DialogDescription className="sr-only">
        {profile ? `Profile card for @${profile.username}` : 'Loading profile'}
      </DialogDescription>

      {isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-muted rounded-lg" />
          <div className="h-16 w-16 bg-muted rounded-full -mt-12 ml-6" />
          <div className="h-6 bg-muted rounded w-1/4 ml-6" />
        </div>
      ) : error || !profile ? (
        <div className="py-12 text-center text-muted-foreground">
          <p className="text-[13px]">Profile not found.</p>
        </div>
      ) : (
        /* Keyed so switching person resets the tab back to its default. */
        <ProfileView
          key={profile.username}
          profile={profile}
          workspaceSlug={workspaceSlug}
          onOpenProfile={onOpenProfile}
        />
      )}
    </>
  );
}
