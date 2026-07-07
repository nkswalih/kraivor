'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, Mail, Building2, Users, Hash, Check, Loader2, X, ThumbsUp } from 'lucide-react';
import { notificationEndpoints, workspaceEndpoints, chatEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { formatRelativeTime } from '@/lib/utils';
import { SkeletonBlock, SkeletonLine } from '@/components/ui/skeletons';
import type { Notification } from '@/types/api';

type InboxTab = 'all' | 'invitations' | 'workspaces' | 'members' | 'channels';

export default function InboxPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore(s => s.user);
  const workspaces = useAuthStore(s => s.workspaces);
  const workspaceId = useAuthStore(s => s.workspaceId);
  const [activeTab, setActiveTab] = useState<InboxTab>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: unreadData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => notificationEndpoints.unreadCount(),
    refetchInterval: 30_000,
  });

  const { data: notifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationEndpoints.list(),
  });

  // My pending invitations (works for users without workspaces)
  const { data: myInvitationsData } = useQuery({
    queryKey: ['invitations', 'mine'],
    queryFn: () => workspaceEndpoints.myPendingInvitations(),
  });

  const { data: allInvitationsData } = useQuery({
    queryKey: ['invitations', 'all'],
    queryFn: async () => {
      const results = await Promise.all(
        (workspaces ?? []).map(w =>
          workspaceEndpoints.listInvitations(w.id).then(invs => ({
            workspaceId: w.id,
            workspaceName: w.name,
            invitations: invs ?? [],
          })).catch(() => ({
            workspaceId: w.id,
            workspaceName: w.name,
            invitations: [],
          }))
        )
      );
      return results;
    },
    enabled: (workspaces?.length ?? 0) > 0,
  });

  const notifs: Notification[] = notifications ?? [];
  const unreadCount = unreadData?.unread_count ?? 0;

  // Pending invitations for current user — combine my-invitations + per-workspace
  const pendingInvites = useMemo(() => {
    const items: { id: string; workspaceName: string; role: string; token: string }[] = [];
    const seen = new Set<string>();
    // Primary source: /invitations/pending/ endpoint (works for all users)
    for (const inv of myInvitationsData ?? []) {
      const token = inv.token;
      if (!seen.has(token)) {
        seen.add(token);
        items.push({
          id: inv.id,
          workspaceName: (inv as any).workspace_name ?? 'Unknown',
          role: inv.role,
          token,
        });
      }
    }
    // Fallback: per-workspace invitations (for admins)
    if (allInvitationsData) {
      for (const ws of allInvitationsData) {
        for (const inv of ws.invitations ?? []) {
          if (inv.status === 'pending' && inv.email === user?.email && !seen.has(inv.token)) {
            seen.add(inv.token);
            items.push({
              id: inv.id,
              workspaceName: ws.workspaceName,
              role: inv.role,
              token: inv.token,
            });
          }
        }
      }
    }
    return items;
  }, [myInvitationsData, allInvitationsData, user?.email]);

  // Category counts
  const workspaceNotifCount = notifs.filter(
    n => n.notification_type?.startsWith('workspace.') && !n.read_at
  ).length;
  const memberNotifCount = notifs.filter(
    n => n.notification_type?.includes('member') && !n.read_at
  ).length;

  const TABS: { id: InboxTab; label: string; icon: React.ElementType; count?: number }[] = [
    { id: 'all', label: 'All', icon: Bell, count: unreadCount },
    { id: 'invitations', label: 'Invitations', icon: Mail, count: pendingInvites.length },
    { id: 'workspaces', label: 'Workspaces', icon: Building2, count: workspaceNotifCount },
    { id: 'members', label: 'Members', icon: Users, count: memberNotifCount },
    { id: 'channels', label: 'Channels', icon: Hash },
  ];

  return (
    <div className="flex flex-1 min-h-0 w-full bg-[#0A0A0B]">
      {/* ─── Sidebar ──────────────────────────────────────── */}
      <aside className="w-[200px] shrink-0 border-r border-[#27272A] bg-[#111113] flex flex-col">
        <div className="h-[49px] flex items-center px-4 border-b border-[#27272A] shrink-0">
          <span className="text-[13px] font-semibold text-[#FAFAFA]">Inbox</span>
        </div>
        <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
          {TABS.map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setSelectedId(null);
                }}
                className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-[6px] text-[13px] font-medium transition-colors text-left ${
                  active
                    ? 'bg-[#27272A] text-[#FAFAFA]'
                    : 'text-[#A1A1AA] hover:bg-[#18181B]/50 hover:text-[#FAFAFA]'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="flex-1">{tab.label}</span>
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="text-[10px] font-semibold bg-venom-yellow text-black min-w-[18px] h-[18px] flex items-center justify-center rounded-full px-1">
                    {tab.count > 99 ? '99+' : tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* ─── Content ──────────────────────────────────────── */}
      <main className="flex-1 flex min-w-0">
        {activeTab === 'all' && (
          <AllPanel
            notifications={notifs}
            selectedId={selectedId}
            onSelect={setSelectedId}
            queryClient={queryClient}
          />
        )}
        {activeTab === 'invitations' && (
          <InvitationsPanel pendingInvites={pendingInvites} queryClient={queryClient} />
        )}
        {activeTab === 'workspaces' && (
          <WorkspacesPanel
            notifications={notifs}
            selectedId={selectedId}
            onSelect={setSelectedId}
            queryClient={queryClient}
          />
        )}
        {activeTab === 'members' && (
          <MembersPanel notifications={notifs} workspaceId={workspaceId ?? undefined} />
        )}
        {activeTab === 'channels' && <ChannelsPanel workspaceId={workspaceId ?? undefined} />}
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════════ */

function acceptInviteInPanel(
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

function notificationDetail(
  n: Notification,
  onDismiss: (id: string) => void,
  acceptMut?: { mutate: (t: string) => void; isPending: boolean }
) {
  const isInvite = n.notification_type === 'workspace.invitation';
  const isFollow = n.notification_type === 'profile.follow.new';
  const token = isInvite && n.link ? n.link.replace('/invitations/', '') : '';
  const followerUsername = isFollow ? (n.metadata?.follower_username as string) : undefined;
  return (
    <div className="space-y-4">
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

/* ═══════════════════════════════════════════════════════════════════
   All Panel — shows ALL notifications
   ═══════════════════════════════════════════════════════════════════ */

function AllPanel({
  notifications,
  selectedId,
  onSelect,
  queryClient,
}: {
  notifications: Notification[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const markReadMut = useMutation({
    mutationFn: (id: string) => notificationEndpoints.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  const dismissMut = useMutation({
    mutationFn: (id: string) => notificationEndpoints.dismiss(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  const acceptMut = useMutation({
    mutationFn: (token: string) => workspaceEndpoints.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
  });

  if (notifications.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[13px] text-[#A1A1AA]">No notifications yet</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-w-0">
      <div className="w-[360px] shrink-0 border-r border-[#27272A] overflow-y-auto">
        <div className="p-3 space-y-1">
          {notifications.map(n => {
            const isInvite = n.notification_type === 'workspace.invitation';
            const isFollow = n.notification_type === 'profile.follow.new';
            const isUpvote = n.notification_type.endsWith('upvoted');
            const token = isInvite && n.link ? n.link.replace('/invitations/', '') : '';
            const followerUsername = isFollow ? (n.metadata?.follower_username as string) : undefined;
            return (
              <div
                key={n.id}
                onClick={() => {
                  onSelect(n.id);
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
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {selectedId ? (
          (() => {
            const n = notifications.find(x => x.id === selectedId);
            if (!n) return <p className="text-[#A1A1AA] text-[13px]">Select a notification</p>;
            return notificationDetail(n, id => dismissMut.mutate(id), acceptMut);
          })()
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[13px] text-[#A1A1AA]">Select a notification to view</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Invitations
   ═══════════════════════════════════════════════════════════════════ */

function InvitationsPanel({
  pendingInvites,
  queryClient,
}: {
  pendingInvites: { id: string; workspaceName: string; role: string; token: string }[];
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const acceptMut = useMutation({
    mutationFn: (token: string) => workspaceEndpoints.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations', 'all'] });
      queryClient.invalidateQueries({ queryKey: ['invitations', 'mine'] });
    },
  });

  if (pendingInvites.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[13px] text-[#A1A1AA]">No pending invitations</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="space-y-2 max-w-[500px]">
        {pendingInvites.map(inv => (
          <div
            key={inv.id}
            className="flex items-center gap-3 p-3 rounded-lg bg-[#111113] border border-[#27272A]"
          >
            <div className="w-9 h-9 rounded-lg bg-[#27272A] flex items-center justify-center text-xs font-bold text-[#FAFAFA] shrink-0">
              {inv.workspaceName.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-[#FAFAFA] truncate">{inv.workspaceName}</p>
              <p className="text-[11px] text-[#A1A1AA]">Invited as {inv.role}</p>
            </div>
            <button
              onClick={() => acceptMut.mutate(inv.token)}
              disabled={acceptMut.isPending}
              className="shrink-0 px-3 py-1.5 bg-venom-yellow hover:bg-venom-gold text-black text-xs font-medium rounded-[6px] transition-colors disabled:opacity-50 flex items-center gap-1"
            >
              {acceptMut.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Check className="w-3.5 h-3.5" />
              )}
              Accept
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Workspaces — workspace.* notifications
   ═══════════════════════════════════════════════════════════════════ */

function WorkspacesPanel({
  notifications,
  selectedId,
  onSelect,
  queryClient,
}: {
  notifications: Notification[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const filtered = useMemo(
    () => notifications.filter(n => n.notification_type?.startsWith('workspace.')),
    [notifications]
  );

  const markReadMut = useMutation({
    mutationFn: (id: string) => notificationEndpoints.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  const dismissMut = useMutation({
    mutationFn: (id: string) => notificationEndpoints.dismiss(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  const acceptMut = useMutation({
    mutationFn: (token: string) => workspaceEndpoints.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
  });

  if (filtered.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[13px] text-[#A1A1AA]">No workspace notifications</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-w-0">
      <div className="w-[360px] shrink-0 border-r border-[#27272A] overflow-y-auto">
        <div className="p-3 space-y-1">
          {filtered.map(n => {
            const isInvite = n.notification_type === 'workspace.invitation';
            const token = isInvite && n.link ? n.link.replace('/invitations/', '') : '';
            return (
              <div
                key={n.id}
                onClick={() => {
                  onSelect(n.id);
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
                <div className="w-9 h-9 rounded-full bg-[#27272A] flex items-center justify-center text-xs font-bold text-[#FAFAFA] shrink-0 mt-0.5">
                  {n.title.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[13px] font-medium text-[#FAFAFA] truncate">{n.title}</p>
                    <span className="text-[10px] text-[#A1A1AA] shrink-0 whitespace-nowrap mt-0.5">
                      {formatRelativeTime(n.created_at)}
                    </span>
                  </div>
                  <p className="text-[12px] text-[#A1A1AA] line-clamp-1 mt-0.5 text-left">
                    {n.body || n.title}
                  </p>
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
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {selectedId ? (
          (() => {
            const n = filtered.find(x => x.id === selectedId);
            if (!n) return <p className="text-[#A1A1AA] text-[13px]">Select a notification</p>;
            return notificationDetail(n, id => dismissMut.mutate(id), acceptMut);
          })()
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[13px] text-[#A1A1AA]">Select a notification to view</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Members — member.* notifications + DM rooms
   ═══════════════════════════════════════════════════════════════════ */

function MembersPanel({
  notifications,
  workspaceId,
}: {
  notifications: Notification[];
  workspaceId?: string;
}) {
  const memberNotifs = useMemo(
    () => notifications.filter(n => n.notification_type?.includes('member')),
    [notifications]
  );

  const { data: rooms } = useQuery({
    queryKey: ['rooms', workspaceId],
    queryFn: () => chatEndpoints.listRooms(workspaceId!),
    enabled: !!workspaceId,
  });

  const roomsList = Array.isArray(rooms) ? rooms : (rooms?.results ?? []);
  const dmRooms = roomsList.filter(r => r.room_type === 'dm');

  if (memberNotifs.length === 0 && dmRooms.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[13px] text-[#A1A1AA]">No member activity</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
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
                <a
                  key={room.id}
                  href={`/${workspaceId}/chat/${room.id}`}
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
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Channels — room list with recent message preview
   ═══════════════════════════════════════════════════════════════════ */

function ChannelsPanel({ workspaceId }: { workspaceId?: string }) {
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

  if (!workspaceId) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[13px] text-[#A1A1AA]">No workspace selected</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 p-4 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-3 p-3 rounded-lg bg-[#111113]">
            <SkeletonBlock className="w-9 h-9 rounded shrink-0" />
            <div className="flex-1 space-y-1">
              <SkeletonLine className="w-1/3" />
              <SkeletonLine className="w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const roomsList = Array.isArray(rooms) ? rooms : (rooms?.results ?? []);
  const channelRooms = roomsList.filter(r => r.room_type !== 'dm');

  if (channelRooms.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-[13px] text-[#A1A1AA]">No channels</p>
      </div>
    );
  }

  const messages = Array.isArray(messagesData) ? messagesData : (messagesData?.results ?? []);

  return (
    <div className="flex flex-1 min-w-0">
      {/* Room list */}
      <div className="w-[280px] shrink-0 border-r border-[#27272A] overflow-y-auto">
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
      </div>

      {/* Message preview */}
      <div className="flex-1 overflow-y-auto p-4">
        {selectedRoom ? (
          messagesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex gap-3">
                  <SkeletonBlock className="w-8 h-8 rounded-full shrink-0" />
                  <div className="flex-1 space-y-1">
                    <SkeletonLine className="w-1/4" />
                    <SkeletonLine className="w-2/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-[13px] text-[#A1A1AA]">No messages yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.slice(0, 20).map((msg: { message_id: string; id: string; sender_name: string; created_at: string; content: string; read_at?: string | null; link?: string; notification_type?: string }) => (
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
              <a
                href={`/${workspaceId}/chat/${selectedRoom}`}
                className="block text-[12px] text-venom-yellow hover:text-venom-gold text-center py-2"
              >
                Open channel →
              </a>
            </div>
          )
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-[13px] text-[#A1A1AA]">Select a channel to view messages</p>
          </div>
        )}
      </div>
    </div>
  );
}
