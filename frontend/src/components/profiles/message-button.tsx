'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Loader2, MessageSquare } from 'lucide-react';
import { chatEndpoints } from '@/lib/api/endpoints';
import { isApiError } from '@/lib/api/error-handler';
import { useAuthStore } from '@/lib/stores/auth-store';

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
  isOwner: boolean;
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

export function MessageButton({ targetUserId, targetName, isOwner }: MessageButtonProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const workspaceId = useAuthStore((s) => s.workspaceId);
  const workspaceSlug = useAuthStore((s) => s.workspaceSlug);
  const accessToken = useAuthStore((s) => s.accessToken);

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

  // `accessToken` rather than `workspaceId` alone: a logged-out visitor browsing
  // the public profile page has no workspace selected, and one with a stale
  // workspace in localStorage has no session. Both would otherwise render a
  // button that fails on press.
  if (isOwner || !workspaceId || !accessToken || !targetUserId) return null;

  const pending = startDm.isPending;

  return (
    <button
      onClick={() => startDm.mutate()}
      disabled={pending}
      aria-busy={pending}
      // `aria-label`, not `title`. A `title` is only the accessible name when
      // nothing else supplies one, and the visible "Message" span always does --
      // so the title became a mouse-only tooltip and screen reader users heard a
      // bare "Message" with no idea who they were about to write to. The label
      // still contains the visible text, which is what WCAG 2.5.3 requires of a
      // control whose name is set this way.
      aria-label={`Message ${targetName}`}
      className="flex items-center gap-2 text-[13px] font-medium px-4 py-1.5 rounded-md border border-venom-yellow/50 bg-venom-yellow/10 text-foreground hover:bg-venom-yellow/20 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
    >
      {pending ? (
        <Loader2 className="size-3.5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
      ) : (
        <MessageSquare className="size-3.5" aria-hidden="true" />
      )}
      <span>{pending ? 'Opening...' : 'Message'}</span>
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