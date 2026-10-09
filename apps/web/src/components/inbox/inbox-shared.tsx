'use client';

import { Check, Loader2 } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';
import type { Notification } from '@/types/api';

/**
 * Pieces two sections share.
 *
 * Lifted straight out of the old `inbox/page.tsx` -- same markup, same classes
 * -- so the move from page to panel changes where these render, not what they
 * render. The invitation token comes off `notification.link` (`/invitations/
 * {token}`) and is the same value the accept mutation posts.
 */

export interface PendingInvite {
  id: string;
  workspaceName: string;
  role: string;
  token: string;
}

/** The accept affordance, shared by the list rows and the detail pane. */
export function acceptInviteInPanel(
  token: string,
  mut: { mutate: (t: string, opts?: { onSuccess?: () => void }) => void; isPending: boolean },
  onAcceptSuccess?: () => void
) {
  return (
    <button
      onClick={() => mut.mutate(token, { onSuccess: onAcceptSuccess })}
      disabled={mut.isPending}
      className="shrink-0 px-2.5 py-1 bg-venom-yellow hover:bg-venom-gold text-black text-[11px] font-medium rounded-[4px] transition-colors disabled:opacity-50 flex items-center gap-1"
    >
      {mut.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
      Accept
    </button>
  );
}

/** The right-hand pane for a selected notification. */
export function notificationDetail(
  n: Notification,
  onDismiss: (id: string) => void,
  acceptMut?: { mutate: (t: string) => void; isPending: boolean }
) {
  const isInvite = n.notification_type === 'workspace.invitation';
  const isFollow = n.notification_type === 'profile.follow.new';
  const token = isInvite && n.link ? n.link.replace('/invitations/', '') : '';
  const followerUsername = isFollow ? (n.metadata?.follower_username as string) : undefined;
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-3">
        {isFollow ? (
          <div className="w-10 h-10 rounded-full bg-venom-yellow flex items-center justify-center text-sm font-bold text-black shrink-0">
            {(followerUsername || 'U').charAt(0).toUpperCase()}
          </div>
        ) : (
          <div className="w-10 h-10 rounded-full bg-[#27272A] flex items-center justify-center text-sm font-bold text-[#FAFAFA] shrink-0">
            {n.title.charAt(0).toUpperCase()}
          </div>
        )}
        <div>
          <p className="text-[15px] font-semibold text-[#FAFAFA]">
            {isFollow ? (followerUsername || 'Someone') : n.title}
          </p>
          <p className="text-[12px] text-[#A1A1AA]">{formatRelativeTime(n.created_at)}</p>
        </div>
      </div>
      {isFollow ? (
        <p className="text-[14px] text-[#D1D5DB] leading-relaxed">Followed you</p>
      ) : n.body ? (
        <p className="text-[14px] text-[#D1D5DB] leading-relaxed whitespace-pre-wrap">{n.body}</p>
      ) : null}
      <div className="flex items-center gap-2 pt-2">
        {isInvite &&
          token &&
          acceptMut &&
          acceptInviteInPanel(token, acceptMut, () => onDismiss(n.id))}
        {n.link && !isInvite && (
          <a href={n.link} className="text-[12px] text-venom-yellow hover:text-venom-gold">
            View details
          </a>
        )}
        <button
          onClick={() => onDismiss(n.id)}
          className="text-[12px] text-[#A1A1AA] hover:text-red-400"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

/** Centred placeholder for a pane with nothing selected yet. */
export function InboxEmpty({ message }: { message: string }) {
  return (
    <div className="flex h-full min-h-[200px] items-center justify-center px-4">
      <p className="text-[13px] text-[#A1A1AA] text-center">{message}</p>
    </div>
  );
}
