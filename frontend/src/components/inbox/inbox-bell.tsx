'use client';

import { Inbox } from 'lucide-react';
import { useInboxDialogStore } from '@/lib/stores/inbox-dialog-store';
import { useUnreadCount } from './use-inbox-data';

/**
 * The topbar's inbox entry point.
 *
 * This is the whole of what remains of `InboxPopover`, which was a 362-line
 * dropdown listing the five most recent notifications. The panel supersedes it
 * on every axis -- it shows the whole feed, not five, and it can filter, accept
 * invitations and open a DM, none of which the popover could -- so keeping both
 * meant two surfaces for one thing, with two code paths that could disagree
 * about the unread count.
 *
 * What the popover did that the panel did not is preserved elsewhere rather
 * than dropped:
 *
 *  - "Mark all read" moved into the panel's All section;
 *  - priming browser audio permission on the first gesture moved into
 *    `DashboardNotificationSocket`, which is where the chime actually plays.
 *
 * The badge reads the same `['unread-count']` key the panel's rail and the
 * socket invalidate, so they cannot drift.
 */
export function InboxBell() {
  const openInbox = useInboxDialogStore(s => s.open);
  const { data } = useUnreadCount();
  const unread = data?.unread_count ?? 0;

  return (
    <button
      type="button"
      onClick={() => openInbox()}
      aria-label={unread > 0 ? `Inbox, ${unread} unread` : 'Inbox'}
      className="relative p-1.5 text-[#A1A1AA] hover:text-[#FAFAFA] transition-colors"
    >
      <Inbox className="w-4 h-4" />
      {unread > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-venom-yellow text-[9px] font-bold text-black flex items-center justify-center">
          {unread > 9 ? '9+' : unread}
        </span>
      )}
    </button>
  );
}
