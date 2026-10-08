'use client';

import { useMemo } from 'react';
import { Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { workspaceEndpoints, profileEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { avatarUrl } from '@/lib/utils';
import type { WorkspaceMember } from '@/types/api';

interface MembersPanelProps {
  workspaceId: string;
  onlineUserIds: Set<string>;
}

type MemberProfile = {
  avatar_url?: string;
  user_avatar_url?: string;
  username?: string;
  display_name?: string;
};

function resolveName(
  member: WorkspaceMember,
  profile: MemberProfile | undefined,
  fallbackUser: { id: string; name: string } | null
) {
  return (
    profile?.username ||
    profile?.display_name ||
    member.user?.name ||
    (fallbackUser && member.user_id === fallbackUser.id ? fallbackUser.name : '') ||
    member.user?.email ||
    'Member'
  );
}

function MemberRow({
  name,
  role,
  src,
  online,
}: {
  name: string;
  role: string;
  src: string | null;
  online: boolean;
}) {
  return (
    <div
      title={`${name} · ${online ? 'Online' : 'Offline'} · ${role}`}
      className={`flex items-center gap-2.5 px-2 py-1.5 rounded-md transition-all hover:bg-krait-surface1/60 ${
        online ? '' : 'opacity-40 hover:opacity-70'
      }`}
    >
      {/* Avatar carries the presence dot, so the row reads at a glance
          (green = here, no dot = away) without a trailing status column. */}
      <div className="relative shrink-0">
        {src ? (
          <img
            src={src}
            alt={name}
            className="w-7 h-7 rounded-full border border-gray-800 object-cover"
          />
        ) : (
          <div className="w-7 h-7 rounded-full bg-krait-surface3 flex items-center justify-center text-[11px] font-bold text-text-primary">
            {name.charAt(0).toUpperCase()}
          </div>
        )}
        {online && (
          <span
            className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-green-400 border-2 border-krait-obsidian"
            aria-label="Online"
          />
        )}
      </div>
      <p className="flex-1 min-w-0 text-[13px] font-medium text-text-primary truncate">{name}</p>
    </div>
  );
}

export function MembersPanel({ workspaceId, onlineUserIds }: MembersPanelProps) {
  const currentUser = useAuthStore(s => s.user);

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['members', workspaceId],
    queryFn: () => workspaceEndpoints.getMembers(workspaceId),
    enabled: !!workspaceId,
  });

  const membersList = members ?? [];

  const memberIds = useMemo(() => membersList.map(m => m.user_id), [membersList]);

  const { data: profilesData } = useQuery({
    queryKey: ['profiles-by-ids', memberIds],
    queryFn: () => profileEndpoints.getProfilesByIds(memberIds),
    enabled: memberIds.length > 0,
    staleTime: 60_000,
  });

  const profileMap = useMemo(() => profilesData?.profiles ?? {}, [profilesData]);

  /* Split into presence buckets, each sorted by display name — online
     first, then everyone else, the way a members list is expected to read. */
  const { online, offline } = useMemo(() => {
    const sorted = [...membersList].sort((a, b) =>
      resolveName(a, profileMap[a.user_id], currentUser).localeCompare(
        resolveName(b, profileMap[b.user_id], currentUser)
      )
    );
    return {
      online: sorted.filter(m => onlineUserIds.has(m.user_id)),
      offline: sorted.filter(m => !onlineUserIds.has(m.user_id)),
    };
  }, [membersList, profileMap, onlineUserIds, currentUser]);

  const isLoading = membersLoading;

  return (
    <div className="w-[220px] bg-krait-obsidian border-l border-krait-border flex flex-col shrink-0 select-none overflow-y-auto">
      <div className="h-[49px] flex items-center gap-2 px-4 border-b border-krait-border shrink-0">
        <Users className="w-4 h-4 text-text-tertiary" />
        <span className="text-[13px] font-semibold text-text-primary">Members</span>
        <span className="text-[11px] text-text-tertiary ml-auto">{membersList.length}</span>
      </div>

      <div className="flex-1 overflow-y-auto py-2 px-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-4 h-4 border-2 border-venom-yellow border-t-transparent rounded-full animate-spin" />
          </div>
        ) : membersList.length === 0 ? (
          <p className="text-[12px] text-text-tertiary px-2 py-4 text-center">No members</p>
        ) : (
          <>
            <p className="px-2 pt-2 pb-1 text-[11px] font-semibold tracking-wider text-text-tertiary">
              Online — {online.length}
            </p>
            <div className="space-y-0.5">
              {online.map(member => {
                const profile = profileMap[member.user_id];
                return (
                  <MemberRow
                    key={member.id}
                    name={resolveName(member, profile, currentUser)}
                    role={member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                    src={
                      avatarUrl(profile?.avatar_url, profile?.user_avatar_url) ||
                      member.user?.avatar_url ||
                      null
                    }
                    online
                  />
                );
              })}
            </div>

            <p className="px-2 pt-4 pb-1 text-[11px] font-semibold tracking-wider text-text-tertiary">
              Offline — {offline.length}
            </p>
            <div className="space-y-0.5">
              {offline.map(member => {
                const profile = profileMap[member.user_id];
                return (
                  <MemberRow
                    key={member.id}
                    name={resolveName(member, profile, currentUser)}
                    role={member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                    src={
                      avatarUrl(profile?.avatar_url, profile?.user_avatar_url) ||
                      member.user?.avatar_url ||
                      null
                    }
                    online={false}
                  />
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
