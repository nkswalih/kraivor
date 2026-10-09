'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Hash } from 'lucide-react';
import { chatEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { formatRelativeTime } from '@/lib/utils';
import { InboxMessagesSkeleton, InboxListSkeleton } from './inbox-skeletons';
import { InboxEmpty } from './inbox-shared';
import { SplitView } from './split-view';

interface PreviewMessage {
  message_id: string;
  /** Present on some payloads and not others; the key falls back to it. */
  id?: string;
  sender_name: string;
  created_at: string;
  content: string;
}

/**
 * Channels: a room list beside a preview of its recent messages.
 *
 * Same split as All and Workspaces, so the responsive rules come from one
 * place instead of being restated a third time -- below `sm` picking a channel
 * swaps the list for the preview with a Back bar, above it they sit side by
 * side.
 *
 * As in Members, `workspaceId` is the UUID for the API calls and
 * `workspaceSlug` is what the one href below is built from; falling through
 * with an empty slug would render `/chat/{room}`, a different route entirely.
 * The "Open channel" link stays inside the branch that maps messages: an empty
 * channel offers no link at all, which is pre-existing gating left alone here.
 */
export function ChannelsSection() {
  const workspaceId = useAuthStore(s => s.workspaceId);
  const workspaceSlug = useParams<{ workspace: string }>()?.workspace ?? '';
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);

  const { data: rooms, isLoading } = useQuery({
    queryKey: ['rooms', workspaceId],
    queryFn: () => chatEndpoints.listRooms(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: messagesData, isLoading: messagesLoading } = useQuery({
    queryKey: ['messages', selectedRoom],
    queryFn: () => chatEndpoints.listMessages(workspaceId!, selectedRoom!),
    enabled: !!selectedRoom && !!workspaceId,
  });

  if (!workspaceId || !workspaceSlug) return <InboxEmpty message="No workspace selected" />;

  if (isLoading) {
    return (
      <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4">
        <InboxListSkeleton rows={5} />
      </div>
    );
  }

  const roomsList = Array.isArray(rooms) ? rooms : (rooms?.results ?? []);
  const channelRooms = roomsList.filter(r => r.room_type !== 'dm');

  if (channelRooms.length === 0) return <InboxEmpty message="No channels" />;

  const messages: PreviewMessage[] = Array.isArray(messagesData)
    ? messagesData
    : (messagesData?.results ?? []);

  return (
    <SplitView
      hasSelection={!!selectedRoom}
      onBack={() => setSelectedRoom(null)}
      list={
        <div className="p-3 space-y-1">
          {channelRooms.map(room => (
            <button
              key={room.id}
              onClick={() => setSelectedRoom(room.id)}
              className={`w-full flex items-center gap-2.5 p-2.5 rounded-lg text-left transition-colors ${
                selectedRoom === room.id ? 'bg-[#27272A]' : 'hover:bg-[#18181B]'
              }`}
            >
              <div className="w-8 h-8 rounded-lg bg-[#27272A] flex items-center justify-center shrink-0">
                <Hash className="w-4 h-4 text-[#A1A1AA]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium text-[#FAFAFA] truncate">#{room.name}</p>
                {room.topic && <p className="text-[11px] text-[#A1A1AA] truncate">{room.topic}</p>}
              </div>
            </button>
          ))}
        </div>
      }
      detail={
        selectedRoom ? (
          messagesLoading ? (
            <div className="p-4">
              <InboxMessagesSkeleton rows={3} />
            </div>
          ) : messages.length === 0 ? (
            <InboxEmpty message="No messages yet" />
          ) : (
            <div className="space-y-3 p-4">
              {messages.slice(0, 20).map(msg => (
                <div key={msg.message_id || msg.id} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#27272A] flex items-center justify-center text-xs font-bold text-[#FAFAFA] shrink-0">
                    {(msg.sender_name || 'U').charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] font-medium text-[#FAFAFA]">
                        {msg.sender_name || 'Unknown'}
                      </span>
                      <span className="text-[10px] text-[#A1A1AA]">
                        {formatRelativeTime(msg.created_at)}
                      </span>
                    </div>
                    <p className="text-[13px] text-[#D1D5DB] mt-0.5 whitespace-pre-wrap break-words">
                      {msg.content}
                    </p>
                  </div>
                </div>
              ))}
              <Link
                href={`/${workspaceSlug}/chat/${selectedRoom}`}
                className="block text-[12px] text-venom-yellow hover:text-venom-gold text-center py-2"
              >
                Open channel →
              </Link>
            </div>
          )
        ) : (
          <InboxEmpty message="Select a channel to view messages" />
        )
      }
    />
  );
}
