'use client';

import { Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { workspaceEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import type { WorkspaceMember } from '@/types/api';

interface MembersPanelProps {
  workspaceId: string;
  onlineUserIds: Set<string>;
}

function MemberRow({ member, online }: { member: WorkspaceMember; online: boolean }) {
  const currentUser = useAuthStore(s => s.user);

  const name = member.user?.name
    || (currentUser && member.user_id === currentUser.id ? currentUser.name : '')
    || member.user?.email
    || member.user_id.slice(0, 8);

  const initial = name.charAt(0).toUpperCase();

  return (
    <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-[4px] hover:bg-white/[0.04] transition-colors group">
      {member.user?.avatar_url ? (
        <img src={member.user.avatar_url} alt={name} className="w-7 h-7 rounded-[4px] object-cover shrink-0" />
      ) : (
        <div className="w-7 h-7 rounded-[4px] bg-[#27272A] flex items-center justify-center text-[11px] font-bold text-[#FAFAFA] shrink-0">
          {initial}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-[#FAFAFA] truncate">{name}</p>
      </div>
      <div
        className={`w-2 h-2 rounded-full shrink-0 ${online ? 'bg-green-400' : 'bg-[#3A3A3D]'}`}
        title={online ? 'Online' : 'Offline'}
      />
    </div>
  );
}

export function MembersPanel({ workspaceId, onlineUserIds }: MembersPanelProps) {
  const { data: members, isLoading } = useQuery({
    queryKey: ['members', workspaceId],
    queryFn: () => workspaceEndpoints.getMembers(workspaceId),
    enabled: !!workspaceId,
  });

  const membersList = members ?? [];

  return (
    <div className="w-[220px] bg-[#111113] border-l border-[#27272A] flex flex-col shrink-0 select-none overflow-y-auto">
      <div className="h-[49px] flex items-center gap-2 px-4 border-b border-[#27272A] shrink-0">
        <Users className="w-4 h-4 text-text-tertiary" />
        <span className="text-[13px] font-semibold text-[#FAFAFA]">Members</span>
        <span className="text-[11px] text-text-tertiary ml-auto">{membersList.length}</span>
      </div>

      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-4 h-4 border-2 border-venom-yellow border-t-transparent rounded-full animate-spin" />
          </div>
        ) : membersList.length === 0 ? (
          <p className="text-[12px] text-text-tertiary px-2 py-4 text-center">No members</p>
        ) : (
          membersList.map((member) => (
            <MemberRow key={member.id} member={member} online={onlineUserIds.has(member.user_id)} />
          ))
        )}
      </div>
    </div>
  );
}
