'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Loader2, MessageSquare } from 'lucide-react';
import { chatEndpoints } from '@/lib/api/endpoints';
import { isApiError } from '@/lib/api/error-handler';
import { useAuthStore } from '@/lib/stores/auth-store';
import { cn } from '@/lib/utils';

/**
 * Why this file exists.
 *
 * The Message button worked in `5fd494c` and was dropped in a later refactor of
 * `ProfileHeader`. There was no replacement anywhere: the endpoint is still
 * routed, `chatEndpoints.createDm` is still exported, and nothing in the app
 * called it. The feature was lost in a change that was not about the feature.
 *
 * Restored here as its own component rather than back inside `ProfileHeader`,
 * because `ProfileHeader` takes a `Profile` and this needs four things that have
 * nothing to do with one: the auth store, react-query, the router, and the room
 * list it invalidates. Its sibling `FollowButton` is already split out for the
 * same reason.
 */

interface MessageButtonProps {
  targetUserId: string;
  targetName: string;
  /**
   * Whether `targetUserId` is the signed-in user. Optional: pass it when the
   * caller knows from the API (`Profile.is_owner`), and omit it when the data
   * does not carry the flag -- `TopContributor` does not. It then falls back to
   * comparing against the stored user id.
   *
   * Falling back matters because the failure is asymmetric. Forget it and a user
   * can be offered a Message button on their own profile, which the backend
   * refuses with a 400 the UI would have to apologise for. Deriving keeps that
   * from depending on every call site remembering.
   */
  isOwner?: boolean;
  /**
   * Icon-only, for use inside a list row where a text button would crowd the
   * name. The accessible name comes from `aria-label` either way.
   */
  compact?: boolean;
}

/**
 * What to tell the user, given the status.
 *
 * Keyed on the status rather than the server's message, because the shared
 * `handleApiError` throws core's text away for 403 (`error-handler.ts:95-98`) and
 * a field-keyed DRF `ValidationError` has no `detail` to read at all. Depending
 * on `ApiException.message` here would mean depending on which branch of that
 * switch ran.
 *
 * Only one status maps to one sentence, and that is the point. `DMCreateView`
 * returns 403 with a single body for "no such account", "left the workspace" and
 * "never was a member" alike, because splitting them would let someone probe for
 * whether an account exists. One sentence per status keeps the UI from
 * reintroducing the distinction the API just closed.
 */
export function describeDmFailure(statusCode: number | undefined): string {
  switch (statusCode) {
    case 400:
      return 'You cannot send a message to yourself.';
    case 401:
      return 'Your session has expired. Sign in again to message them.';
    case 403:
      return 'You can only message people who are members of this workspace.';
    case 429:
      return 'Too many messages sent. Wait a moment and try again.';
    default:
      return 'Could not start the conversation. Try again.';
  }
}

export function MessageButton({
  targetUserId,
  targetName,
  isOwner,
  compact = false,
}: MessageButtonProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const workspaceId = useAuthStore((s) => s.workspaceId);
  const workspaceSlug = useAuthStore((s) => s.workspaceSlug);
  const accessToken = useAuthStore((s) => s.accessToken);
  const currentUser = useAuthStore((s) => s.user);

  const startDm = useMutation({
    mutationFn: () =>
      chatEndpoints.createDm(workspaceId!, targetUserId, targetName),
    onSuccess: (room) => {
      // Every room list in the app is keyed `['rooms', workspaceId]` -- the
      // channel sidebar, the dashboard hook and the layout sidebar. Without this
      // the conversation is invisible until something else happens to refetch.
      queryClient.invalidateQueries({ queryKey: ['rooms', workspaceId] });
      router.push(`/${workspaceSlug}/chat/${room.id}`);
    },
    onError: (error) => {
      toast.error(describeDmFailure(isApiError(error) ? error.statusCode : undefined));
    },
  });

  // Two independent signals, ORed rather than ranked. `isOwner` is the server's
  // claim (`Profile.is_owner`); the id comparison is a fact derived from the
  // session. They are ORed because which one actually works depends on `User.id`
  // and `Profile.user_id` sharing an id space -- if they do, the fact decides;
  // if they do not, the prop is the only one that can. Either one saying "this
  // is you" hides the button, so a caller that simply has no `is_owner` at all
  // (`TopContributor` does not) is not a hole.
  const self =
    isOwner === true ||
    (currentUser !== null &&
      currentUser.id !== undefined &&
      currentUser.id === targetUserId);

  // `accessToken` rather than `workspaceId` alone: a logged-out visitor browsing
  // the public profile page has no workspace selected, and one with a stale
  // workspace in localStorage has no session. Both would otherwise render a
  // button that fails on press.
  if (self || !workspaceId || !accessToken || !targetUserId) return null;

  const pending = startDm.isPending;

  return (
    <button
      onClick={() => startDm.mutate()}
      disabled={pending}
      aria-busy={pending}
      // `aria-label`, not `title`, in both modes. A `title` is only the
      // accessible name when nothing else supplies one, and in the full mode the
      // visible "Message" span always did -- so the original `title` became a
      // mouse-only tooltip and screen readers heard a bare "Message" with no idea
      // who they were about to write to. In compact mode there is no text at all,
      // so `title` would have been the only name, carrying the same problem.
      //
      // The label contains the visible text ("Message ..." contains "Message"),
      // which is what WCAG 2.5.3 asks of a control named this way.
      aria-label={`Message ${targetName}`}
      className={cn(
        'flex items-center border border-venom-yellow/50 bg-venom-yellow/10 text-foreground hover:bg-venom-yellow/20 transition-colors disabled:opacity-60 disabled:cursor-not-allowed',
        compact
          // Icon-only, for list rows. `p-2` plus a 14px icon is 30px, clear of
          // WCAG 2.5.8's 24x24 target size, which the bare icon would not reach.
          ? 'p-2 rounded-md'
          : 'gap-2 text-[13px] font-medium px-4 py-1.5 rounded-md'
      )}
    >
      {pending ? (
        <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
      ) : (
        <MessageSquare className="size-3.5" aria-hidden="true" />
      )}
      {!compact && <span>{pending ? 'Opening...' : 'Message'}</span>}
      {/* The accessible name deliberately does not change when the visible text
          does. `aria-busy` on a button is not reliably announced, so the state
          change would be silent. A visually hidden live region says it outright --
          the same `sr-only role="status"` pattern the analysis progress readout
          uses. */}
      <span className="sr-only" role="status">
        {pending ? `Opening a conversation with ${targetName}` : ''}
      </span>
    </button>
  );
}