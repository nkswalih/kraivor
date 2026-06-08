'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Hash, Plus, Loader2, Edit3, Trash2, X, Check } from 'lucide-react';
import { chatEndpoints } from '@/lib/api/endpoints';
import { CreateChannelDialog } from './create-channel-dialog';

interface ChannelSidebarProps {
  workspaceId: string;
  workspaceSlug: string;
  currentRoomId?: string;
}

export function ChannelSidebar({ workspaceId, workspaceSlug, currentRoomId }: ChannelSidebarProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const { data: rooms, isLoading } = useQuery({
    queryKey: ['rooms', workspaceId],
    queryFn: () => chatEndpoints.listRooms(workspaceId),
    enabled: !!workspaceId,
  });

  const renameMut = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      chatEndpoints.updateRoom(workspaceId, id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms', workspaceId] });
      setEditingId(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => chatEndpoints.archiveRoom(workspaceId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms', workspaceId] });
      if (currentRoomId) {
        router.push(`/${workspaceSlug}/chat`);
      }
    },
  });

  if (isLoading) {
    return (
      <div className="w-[260px] bg-[#111113] border-r border-[#27272A] flex items-center justify-center shrink-0">
        <Loader2 className="w-5 h-5 text-venom-yellow animate-spin" />
      </div>
    );
  }

  const roomsList = Array.isArray(rooms) ? rooms : (rooms?.results ?? []);
  const channels = roomsList.filter(r => r.room_type === 'workspace' || r.room_type === 'group');
  const dms = roomsList.filter(r => r.room_type === 'dm');

  return (
    <div className="w-[260px] bg-[#111113] border-r border-[#27272A] flex flex-col shrink-0 select-none">
      {/* Header */}
      <div className="h-[48px] flex items-center justify-between px-4 border-b border-[#27272A] shrink-0 shadow-sm">
        <span className="text-[15px] font-bold text-[#FAFAFA] tracking-tight">Chat</span>
      </div>

      {/* Lists Container */}
      <div className="flex-1 overflow-y-auto py-4 space-y-6">
        
        {/* Channels Section */}
        <div>
          <div className="flex items-center justify-between px-4 mb-1.5 group">
            <span className="text-[12px] font-bold tracking-wider text-text-tertiary uppercase">Channels</span>
            <button
              onClick={() => setShowCreate(true)}
              className="text-text-tertiary hover:text-[#FAFAFA] transition-colors p-0.5 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              title="Create channel"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          
          <div className="space-y-[2px]">
            {channels.length === 0 && (
              <p className="text-[13px] text-text-tertiary px-4 py-2">No channels yet</p>
            )}
            {channels.map((room) => {
              const active = room.id === currentRoomId;
              const isEditing = editingId === room.id;

              if (isEditing) {
                return (
                  <div key={room.id} className="flex items-center gap-1.5 px-2 py-1.5 mx-2 bg-[#0A0A0B] border border-[#6366F1] rounded-md shadow-sm">
                    <Hash className="w-5 h-5 shrink-0 text-text-tertiary opacity-70" />
                    <input
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      className="flex-1 bg-transparent text-[14px] font-medium text-[#FAFAFA] focus:outline-none min-w-0"
                      autoFocus
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          if (editName.trim()) renameMut.mutate({ id: room.id, name: editName.trim() });
                        }
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                    />
                    <div className="flex items-center shrink-0">
                      <button
                        onClick={() => editName.trim() && renameMut.mutate({ id: room.id, name: editName.trim() })}
                        className="p-1 text-green-400 hover:text-green-300 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-green-400"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-1 text-text-tertiary hover:text-[#FAFAFA] rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={room.id}
                  className={`group flex items-center mx-2 rounded-md transition-colors ${
                    active
                      ? 'bg-[#27272A] text-[#FAFAFA]'
                      : 'text-text-secondary hover:bg-white/[0.04] hover:text-[#FAFAFA]'
                  }`}
                >
                  <Link
                    href={`/${workspaceSlug}/chat/${room.id}`}
                    className="flex-1 flex items-center gap-1.5 px-2 py-1.5 min-w-0 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    <Hash className={`w-5 h-5 shrink-0 transition-colors ${active ? 'text-inherit' : 'text-text-tertiary group-hover:text-inherit'}`} />
                    <span className="truncate text-[14px] font-medium">{room.name}</span>
                  </Link>

                  {/* Hover actions */}
                  <div className="hidden group-hover:flex items-center gap-0.5 pr-1.5 shrink-0">
                    <button
                      onClick={(e) => { e.preventDefault(); setEditingId(room.id); setEditName(room.name); }}
                      className="p-1.5 text-text-tertiary hover:text-[#FAFAFA] transition-colors rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 bg-[#111113] group-hover:bg-transparent"
                      title="Rename"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => { e.preventDefault(); if (confirm(`Archive #${room.name}?`)) deleteMut.mutate(room.id); }}
                      className="p-1.5 text-text-tertiary hover:text-red-400 transition-colors rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 bg-[#111113] group-hover:bg-transparent"
                      title="Archive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Direct Messages Section */}
        <div>
          <div className="flex items-center justify-between px-4 mb-1.5">
            <span className="text-[12px] font-bold tracking-wider text-text-tertiary uppercase">Direct Messages</span>
          </div>
          <div className="space-y-[2px]">
            {dms.length === 0 && (
              <p className="text-[13px] text-text-tertiary px-4 py-2">No conversations</p>
            )}
            {dms.map((room) => {
              const active = room.id === currentRoomId;
              return (
                <div 
                  key={room.id}
                  className={`group flex items-center mx-2 rounded-md transition-colors ${
                    active
                      ? 'bg-[#27272A] text-[#FAFAFA]'
                      : 'text-text-secondary hover:bg-white/[0.04] hover:text-[#FAFAFA]'
                  }`}
                >
                  <Link
                    href={`/${workspaceSlug}/chat/${room.id}`}
                    className="flex-1 flex items-center gap-3 px-2 py-1.5 min-w-0 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    <div className="w-8 h-8 rounded-full bg-[#27272A] flex items-center justify-center text-[13px] font-bold text-[#FAFAFA] shrink-0">
                      {room.name.charAt(0).toUpperCase()}
                    </div>
                    <span className="truncate text-[14px] font-medium">{room.name}</span>
                  </Link>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      <CreateChannelDialog
        workspaceId={workspaceId}
        workspaceSlug={workspaceSlug}
        open={showCreate}
        onClose={() => setShowCreate(false)}
      />
    </div>
  );
}