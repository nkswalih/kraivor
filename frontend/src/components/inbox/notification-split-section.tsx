'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ThumbsUp } from 'lucide-react';
import { notificationEndpoints, workspaceEndpoints } from '@/lib/api/endpoints';
import { formatRelativeTime } from '@/lib/utils';
import type { Notification } from '@/types/api';
import { acceptInviteInPanel, InboxEmpty, notificationDetail } from './inbox-shared';
import { InboxSplitSkeleton } from './inbox-skeletons';
import { SplitView } from './split-view';
import { useNotifications } from './use-inbox-data';

interface NotificationSplitSectionProps {
  /** Narrows the list; omit for every notification. */
  filter?: (n: Notification) => boolean;
  /** Shown when the request resolves to nothing. */
  emptyMessage: string;
}

/**
 * List-beside-detail over the notification feed.
 *
 * `AllSection` and `WorkspacesSection` are this component with a different
 * `filter` and a different empty string -- they were two ~120-line copies in
 * the old page, kept apart only by which notifications they selected. One
 * implementation means a fix to the row markup or the accept/dismiss wiring
 * lands in both, and the filter is the entire difference between them.
 *
 * Fetches its own list rather than taking it as a prop: that is what lets the
 * section be a lazily imported chunk with no wiring, and React Query hands it
 * the data the nav rail already pulled for its badge. Selection is local
 * state, which reproduces the old "switching tabs clears the selection"
 * behavior for free -- the section unmounts when you leave it.
 */
export function NotificationSplitSection({
  filter,
  emptyMessage,
}: NotificationSplitSectionProps) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: notifications, isLoading } = useNotifications();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
    queryClient.invalidateQueries({ queryKey: ['unread-count'] });
  };

  const markReadMut = useMutation({
    mutationFn: (id: string) => notificationEndpoints.markRead(id),
    onSuccess: invalidate,
  });

  const dismissMut = useMutation({
    mutationFn: (id: string) => notificationEndpoints.dismiss(id),
    onSuccess: invalidate,
  });

  const acceptMut = useMutation({
    mutationFn: (token: string) => workspaceEndpoints.acceptInvitation(token),
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
  });

  /* Shimmer until the list lands. The old page printed the empty string here
     for as long as the request took, which read as an empty feed. */
  if (isLoading) return <InboxSplitSkeleton rows={5} />;

  const all: Notification[] = notifications ?? [];
  const notifs = filter ? all.filter(filter) : all;

  if (notifs.length === 0) return <InboxEmpty message={emptyMessage} />;

  const selected = selectedId ? notifs.find(x => x.id === selectedId) : undefined;

  return (
    <SplitView
      hasSelection={!!selectedId}
      onBack={() => setSelectedId(null)}
      list={
        <div className="p-3 space-y-1">
          {notifs.map(n => {
            const isInvite = n.notification_type === 'workspace.invitation';
            const isFollow = n.notification_type === 'profile.follow.new';
            const isUpvote = n.notification_type.endsWith('upvoted');
            const token = isInvite && n.link ? n.link.replace('/invitations/', '') : '';
            const followerUsername = isFollow
              ? (n.metadata?.follower_username as string)
              : undefined;
            return (
              <div
                key={n.id}
                onClick={() => {
                  setSelectedId(n.id);
                  if (!n.read_at) markReadMut.mutate(n.id);
                }}
                className={`w-full flex gap-3 p-3 rounded-lg text-left transition-colors cursor-pointer ${
                  selectedId === n.id
                    ? 'bg-[#27272A]'
                    : n.read_at
                      ? 'hover:bg-[#18181B]'
                      : 'bg-venom-yellow/5 hover:bg-venom-yellow/10'
                }`}
              >
                {isFollow ? (
                  <div className="w-10 h-10 rounded-full bg-venom-yellow flex items-center justify-center shrink-0">
                    <span className="text-sm font-bold text-black">
                      {(followerUsername || 'U').charAt(0).toUpperCase()}
                    </span>
                  </div>
                ) : isUpvote ? (
                  <div className="w-9 h-9 rounded-full bg-venom-yellow/15 flex items-center justify-center shrink-0 mt-0.5">
                    <ThumbsUp className="w-4 h-4 text-venom-yellow" />
                  </div>
                ) : (
                  <div className="w-9 h-9 rounded-full bg-[#27272A] flex items-center justify-center text-xs font-bold text-[#FAFAFA] shrink-0 mt-0.5">
                    {n.title.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    {isFollow ? (
                      <p className="text-[13px] font-semibold text-[#FAFAFA] truncate">
                        {followerUsername || 'Someone'}
                      </p>
                    ) : (
                      <p className="text-[13px] font-medium text-[#FAFAFA] truncate">{n.title}</p>
                    )}
                    <span className="text-[10px] text-[#A1A1AA] shrink-0 whitespace-nowrap mt-0.5">
                      {formatRelativeTime(n.created_at)}
                    </span>
                  </div>
                  {isFollow ? (
                    <p className="text-[12px] text-[#A1A1AA] mt-0.5 text-left">Followed you</p>
                  ) : (
                    <p className="text-[12px] text-[#A1A1AA] line-clamp-1 mt-0.5 text-left">
                      {n.body || n.title}
                    </p>
                  )}
                </div>
                {isInvite && token && (
                  <div onClick={e => e.stopPropagation()}>
                    {acceptInviteInPanel(token, acceptMut, () => dismissMut.mutate(n.id))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      }
      detail={
        selected ? (
          notificationDetail(selected, id => dismissMut.mutate(id), acceptMut)
        ) : (
          <InboxEmpty message="Select a notification to view" />
        )
      }
    />
  );
}
