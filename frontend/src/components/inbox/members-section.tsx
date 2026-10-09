'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { chatEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { formatRelativeTime } from '@/lib/utils';
import { InboxCardSkeleton, InboxListSkeleton } from './inbox-skeletons';
import { InboxEmpty } from './inbox-shared';
import { useNotifications } from './use-inbox-data';

/**
 * Member activity plus the DM rooms, as one stack.
 *
 * The two identifiers here are deliberately different and this is the only
 * place in the app that needs both at once:
 *
 *  - `workspaceId` (a UUID, from the auth store) is for `listRooms`, which is
 *    an API path -- swapping in the slug turns a working request into a 404
 *    on the server;
 *  - `workspaceSlug` (from the URL) is for the `href` below -- `/${uuid}/chat/…`
 *    matches no route, so every DM row here used to 404 while the identical
 *    link in the channel sidebar, which reads the slug, worked.
 *
 * Getting either one wrong is invisible in one direction and fatal in the
 * other, which is why both are pinned by tests.
 */
export function MembersSection() {
  const workspaceId = useAuthStore(s => s.workspaceId);
  const workspaceSlug = useParams<{ workspace: string }>()?.workspace ?? '';

  const { data: notifications, isLoading: notifsLoading } = useNotifications();

  const { data: rooms, isLoading: roomsLoading } = useQuery({
    queryKey: ['rooms', workspaceId],
    queryFn: () => chatEndpoints.listRooms(workspaceId!),
    enabled: !!workspaceId,
  });

  const memberNotifs = (notifications ?? []).filter(n =>
    n.notification_type?.includes('member')
  );

  const roomsList = Array.isArray(rooms) ? rooms : (rooms?.results ?? []);
  const dmRooms = roomsList.filter(r => r.room_type === 'dm');

  if (notifsLoading || (roomsLoading && !!workspaceId)) {
    return (
      <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4">
        <div className="max-w-[500px] space-y-6">
          <div>
            <p className="text-[10px] font-semibold tracking-wider text-[#A1A1AA] uppercase mb-2">
              Activity
            </p>
            <InboxListSkeleton rows={3} />
          </div>
          <div>
            <p className="text-[10px] font-semibold tracking-wider text-[#A1A1AA] uppercase mb-2">
              Direct Messages
            </p>
            <InboxCardSkeleton rows={3} />
          </div>
        </div>
      </div>
    );
  }

  if (memberNotifs.length === 0 && dmRooms.length === 0) {
    return <InboxEmpty message="No member activity" />;
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4">
      <div className="max-w-[500px] space-y-6">
        {memberNotifs.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold tracking-wider text-[#A1A1AA] uppercase mb-2">
              Activity
            </p>
            <div className="space-y-1">
              {memberNotifs.map(n => (
                <div
                  key={n.id}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg ${n.read_at ? '' : 'bg-venom-yellow/5'}`}
                >
                  <div className="w-8 h-8 rounded-full bg-[#27272A] flex items-center justify-center text-xs font-bold text-[#FAFAFA] shrink-0">
                    {n.title.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] text-[#FAFAFA] truncate">{n.title}</p>
                    <p className="text-[11px] text-[#A1A1AA] line-clamp-1">{n.body}</p>
                  </div>
                  <span className="text-[10px] text-[#A1A1AA] shrink-0">
                    {formatRelativeTime(n.created_at)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {dmRooms.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold tracking-wider text-[#A1A1AA] uppercase mb-2">
              Direct Messages
            </p>
            <div className="space-y-1">
              {dmRooms.map(room => (
                <Link
                  key={room.id}
                  href={`/${workspaceSlug}/chat/${room.id}`}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[#18181B] transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-[#27272A] flex items-center justify-center text-xs font-bold text-[#FAFAFA] shrink-0">
                    {room.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-medium text-[#FAFAFA] truncate">{room.name}</p>
                    {room.last_message_at && (
                      <p className="text-[10px] text-[#A1A1AA]">
                        {formatRelativeTime(room.last_message_at)}
                      </p>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
