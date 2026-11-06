'use client';

import { cn } from '@/lib/utils';
import type { InboxSection } from '@/lib/stores/inbox-dialog-store';
import { INBOX_SECTIONS } from './inbox-sections';
import { useNotifications, usePendingInvites, useUnreadCount } from './use-inbox-data';

interface InboxSidebarProps {
  active: InboxSection;
  onSelect: (section: InboxSection) => void;
}

/**
 * The left column of the inbox panel -- the nav rail with its counts.
 *
 * It reads the shared registry rather than carrying its own list, so the rail
 * cannot drift from what the dialog would actually render. Items are buttons
 * and not links on purpose: unlike settings, the inbox has one route and no
 * per-section URLs, so an `href` here would point every item at the same
 * address and misrepresent what clicking does.
 *
 * The rail is also what makes the panel feel instant. It subscribes to the
 * unread count, the notification feed and both invitation queries purely to
 * draw its badges -- and because React Query keys those, the three sections
 * that need the same data find it already warm. The badges are a prefetch
 * nobody has to ask for.
 *
 * Below `sm` it unrolls into a horizontal, scrollable strip under the panel's
 * header; at `sm` and up it is the vertical 200px rail the page used to draw.
 * Both are CSS classes, so the two layouts cannot disagree about which section
 * is active. It draws no title of its own -- the panel owns one full-width
 * header row, which is also what absorbs the dialog's close button.
 */
export function InboxSidebar({ active, onSelect }: InboxSidebarProps) {
  const { data: unreadData } = useUnreadCount();
  const { data: notifications } = useNotifications();
  const { data: pendingInvites } = usePendingInvites();

  const notifs = notifications ?? [];
  const unreadCount = unreadData?.unread_count ?? 0;

  const workspaceNotifCount = notifs.filter(
    n => n.notification_type?.startsWith('workspace.') && !n.read_at
  ).length;
  const memberNotifCount = notifs.filter(
    n => n.notification_type?.includes('member') && !n.read_at
  ).length;

  const counts: Partial<Record<InboxSection, number>> = {
    all: unreadCount,
    invitations: pendingInvites.length,
    workspaces: workspaceNotifCount,
    members: memberNotifCount,
  };

  return (
    <aside className="shrink-0 min-h-0 bg-[#111113] border-b border-[#27272A] flex flex-col sm:w-[200px] sm:border-b-0 sm:border-r">
      <nav
        aria-label="Inbox sections"
        className="flex sm:flex-col gap-1 px-2 py-2 min-h-0 overflow-x-auto sm:overflow-x-visible sm:overflow-y-auto sm:flex-1 overscroll-contain"
      >
        {INBOX_SECTIONS.map(section => {
          const Icon = section.icon;
          const isActive = section.id === active;
          const count = counts[section.id] ?? 0;
          return (
            <button
              key={section.id}
              type="button"
              onClick={() => onSelect(section.id)}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex shrink-0 items-center gap-2.5 px-3 py-1.5 rounded-[6px] text-[13px] font-medium transition-colors text-left',
                'sm:w-full',
                isActive
                  ? 'bg-[#27272A] text-[#FAFAFA]'
                  : 'text-[#A1A1AA] hover:bg-[#18181B]/50 hover:text-[#FAFAFA]'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="whitespace-nowrap">{section.label}</span>
              {count > 0 && (
                <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-venom-yellow text-[10px] font-semibold text-black px-1 sm:ml-auto">
                  {count > 99 ? '99+' : count}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
