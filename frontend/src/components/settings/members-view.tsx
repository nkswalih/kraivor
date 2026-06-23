'use client';

import { useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Loader2, Trash2, Mail, Search, X, UserPlus, Users,
} from 'lucide-react';
import { workspaceEndpoints, profileEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import type { WorkspaceMember, WorkspaceInvitation } from '@/types/api';
import { cn } from '@/lib/utils';

type Role = 'owner' | 'admin' | 'member' | 'viewer';
type Filter = 'all' | 'online' | 'admin' | 'member' | 'viewer';

const roleBadge: Record<Role, { label: string; style: string }> = {
  owner: { label: 'Owner', style: 'bg-primary/15 text-primary border border-primary/25' },
  admin: { label: 'Admin', style: 'bg-venom-gold/10 text-venom-gold border border-venom-gold/25' },
  member: { label: 'Member', style: 'bg-blue-500/10 text-blue-400 border border-blue-500/25' },
  viewer: { label: 'Viewer', style: 'bg-muted text-text-tertiary border border-krait-border' },
};

export function MembersView() {
  const params = useParams<{ workspace: string }>();
  const currentSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);
  const currentUser = useAuthStore(s => s.user);
  const workspaces = useAuthStore(s => s.workspaces);
  const selectedWorkspace = (workspaces ?? []).find(w => w.id === workspaceId);

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-text-tertiary text-[13px]">No workspace selected</p>
      </div>
    );
  }

  return (
    <MembersContent
      workspaceId={workspaceId}
      currentUser={currentUser}
      workspaceName={selectedWorkspace?.name ?? ''}
    />
  );
}

function MembersContent({
  workspaceId,
  currentUser,
  workspaceName,
}: {
  workspaceId: string;
  currentUser: { id: string; name?: string; email?: string } | null;
  workspaceName: string;
}) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<Role>('member');
  const [inviteError, setInviteError] = useState('');

  const { data: members = [], isLoading: membersLoading } = useQuery({
    queryKey: ['members', workspaceId],
    queryFn: () => workspaceEndpoints.getMembers(workspaceId),
  });

  const memberIds = useMemo(() => members.map(m => m.user_id), [members]);

  const { data: profilesData } = useQuery({
    queryKey: ['profiles-by-ids', memberIds],
    queryFn: () => profileEndpoints.getProfilesByIds(memberIds),
    enabled: memberIds.length > 0,
    staleTime: 60_000,
  });

  const profileMap = useMemo(() => profilesData?.profiles ?? {}, [profilesData]);

  const { data: invitationsData = [], isLoading: invitationsLoading } = useQuery({
    queryKey: ['invitations', workspaceId],
    queryFn: () => workspaceEndpoints.listInvitations(workspaceId),
  });

  const inviteMut = useMutation({
    mutationFn: () =>
      workspaceEndpoints.inviteMember(workspaceId, { email: inviteEmail, role: inviteRole }),
    onSuccess: () => {
      setInviteEmail('');
      setInviteError('');
      queryClient.invalidateQueries({ queryKey: ['invitations', workspaceId] });
      queryClient.invalidateQueries({ queryKey: ['members', workspaceId] });
    },
    onError: (err: any) => {
      setInviteError(err?.response?.data?.message || err?.message || 'Invitation failed');
    },
  });

  const removeMemberMut = useMutation({
    mutationFn: (userId: string) => workspaceEndpoints.removeMember(workspaceId, userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['members', workspaceId] }),
  });

  const revokeInviteMut = useMutation({
    mutationFn: (invitationId: string) =>
      workspaceEndpoints.revokeInvitation(workspaceId, invitationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations', workspaceId] }),
  });

  const pendingInvitations: WorkspaceInvitation[] = invitationsData.filter(
    inv => inv.status === 'pending'
  );

  const filteredMembers = useMemo(() => {
    let list = [...members];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(m => {
        const prof = profileMap[m.user_id];
        const displayName = prof?.display_name ?? prof?.username ?? '';
        const email = m.user?.email ?? '';
        return displayName.toLowerCase().includes(q) || email.toLowerCase().includes(q);
      });
    }
    if (filter === 'online') {
      list = list.filter(m => m.user_id === currentUser?.id);
    } else if (filter !== 'all') {
      list = list.filter(m => m.role === filter);
    }
    return list;
  }, [members, search, filter, currentUser, profileMap]);

  const onlineMemberIds = useMemo(
    () => new Set(currentUser?.id ? [currentUser.id] : []),
    [currentUser]
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">Members</h2>
        <p className="text-[12px] text-text-secondary mt-1">
          {workspaceName} &middot; {members.length} {members.length === 1 ? 'member' : 'members'}
        </p>
      </div>

      {/* Invite */}
      <div className="bg-krait-surface-1 border border-krait-border rounded-xl p-5">
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">
              Invite by email
            </label>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" />
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full bg-background border border-krait-border rounded-lg pl-9 pr-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors"
                  onKeyDown={e => e.key === 'Enter' && !inviteMut.isPending && inviteMut.mutate()}
                />
              </div>
              <select
                value={inviteRole}
                onChange={e => setInviteRole(e.target.value as Role)}
                className="bg-background border border-krait-border rounded-lg px-2.5 py-2 text-[12px] text-text-secondary focus:outline-none focus:border-primary"
              >
                <option value="admin">Admin</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
          </div>
          <button
            onClick={() => inviteMut.mutate()}
            disabled={!inviteEmail || inviteMut.isPending}
            className="bg-primary hover:bg-primary-dark text-primary-foreground font-medium py-2 px-5 rounded-lg transition-all duration-150 text-[13px] disabled:opacity-40 flex items-center gap-1.5 shrink-0 active:scale-[0.98]"
          >
            {inviteMut.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <UserPlus className="w-3.5 h-3.5" />
            )}
            Invite
          </button>
        </div>
        {inviteError && <p className="text-[12px] text-destructive mt-2">{inviteError}</p>}
      </div>

      {/* Search + Filter */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-[360px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search members..."
            className="w-full bg-krait-surface-1 border border-krait-border rounded-lg pl-9 pr-8 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-1">
          {(['all', 'online', 'admin', 'member', 'viewer'] as Filter[]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-150 capitalize',
                filter === f
                  ? 'bg-primary/15 text-primary border border-primary/25'
                  : 'text-text-tertiary hover:text-text-secondary border border-transparent'
              )}
            >
              {f === 'online' ? 'Online' : f}
            </button>
          ))}
        </div>
      </div>

      {/* Online Section */}
      {onlineMemberIds.size > 0 && search === '' && filter === 'all' && (
        <div>
          <SectionLabel>Online ({onlineMemberIds.size})</SectionLabel>
          <div className="border border-krait-border rounded-xl overflow-hidden divide-y divide-krait-border">
            {members.filter(m => onlineMemberIds.has(m.user_id)).map(m => (
              <MemberRow
                key={m.id}
                member={m}
                profile={profileMap[m.user_id]}
                isMe
                currentUserEmail={currentUser?.email}
                onRemove={() => removeMemberMut.mutate(m.user_id)}
                online
              />
            ))}
          </div>
        </div>
      )}

      {/* All Members Section */}
      <div>
        <SectionLabel>
          {search || filter !== 'all'
            ? `Results (${filteredMembers.length})`
            : `All Members (${filteredMembers.length})`}
        </SectionLabel>

        {membersLoading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="w-5 h-5 animate-spin text-text-tertiary" />
          </div>
        ) : filteredMembers.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Users className="w-8 h-8 text-text-tertiary mb-3" />
            <p className="text-[13px] text-text-tertiary">
              {search ? 'No members match your search.' : 'No members yet.'}
            </p>
            {!search && (
              <p className="text-[11px] text-text-tertiary mt-1">Invite someone above to get started.</p>
            )}
          </div>
        ) : (
          <div className="border border-krait-border rounded-xl overflow-hidden divide-y divide-krait-border">
            {filteredMembers.map(m => (
              <MemberRow
                key={m.id}
                member={m}
                profile={profileMap[m.user_id]}
                isMe={m.user_id === currentUser?.id}
                currentUserEmail={currentUser?.email}
                onRemove={() => removeMemberMut.mutate(m.user_id)}
                online={onlineMemberIds.has(m.user_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Pending Invitations */}
      {invitationsLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="w-4 h-4 animate-spin text-text-tertiary" />
        </div>
      ) : pendingInvitations.length > 0 ? (
        <div>
          <SectionLabel>Pending Invitations ({pendingInvitations.length})</SectionLabel>
          <div className="border border-krait-border rounded-xl overflow-hidden divide-y divide-krait-border">
            {pendingInvitations.map(inv => (
              <div key={inv.id} className="flex items-center gap-3 px-5 py-3.5 group hover:bg-krait-surface-1/50 transition-colors">
                <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center text-sm font-bold text-text-secondary shrink-0">
                  {inv.email.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] text-text-primary truncate">{inv.email}</p>
                  <p className="text-[11px] text-text-tertiary">
                    {inv.role} &middot; Expires {new Date(inv.expires_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="text-[10px] font-medium text-venom-amber bg-venom-amber/10 px-2 py-0.5 rounded-full border border-venom-amber/20">
                  Pending
                </span>
                <button
                  onClick={() => revokeInviteMut.mutate(inv.id)}
                  disabled={revokeInviteMut.isPending}
                  className="p-1.5 text-text-tertiary hover:text-destructive opacity-0 group-hover:opacity-100 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/* ── Sub Components ──────────────────────────────────────────────────── */

function MemberRow({
  member,
  profile,
  isMe,
  currentUserEmail,
  onRemove,
  online,
}: {
  member: WorkspaceMember;
  profile?: { display_name: string; avatar_url: string; user_avatar_url: string; username: string };
  isMe: boolean;
  currentUserEmail?: string;
  onRemove: () => void;
  online?: boolean;
}) {
  const displayName = profile?.display_name ?? profile?.username ?? member.user?.name ?? (isMe ? 'You' : member.user_id.slice(0, 8));
  const username = profile?.username ?? member.user?.email?.split('@')[0] ?? '';
  const email = member.user?.email ?? currentUserEmail ?? '';
  const avatarSrc = profile?.avatar_url ?? profile?.user_avatar_url ?? member.user?.avatar_url ?? null;
  const initials = displayName
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
  const joined = member.joined_at
    ? new Date(member.joined_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—';
  const role = member.role as Role;
  const badge = roleBadge[role] || roleBadge.member;

  return (
    <div className="flex items-center gap-3 px-5 py-3 hover:bg-krait-surface-1/50 transition-colors group min-h-[60px]">
      {/* Avatar */}
      {avatarSrc ? (
        <img src={avatarSrc} alt="" className="w-9 h-9 rounded-full object-cover shrink-0" />
      ) : (
        <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold shrink-0">
          {initials}
        </div>
      )}

      {/* Info */}
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <p className="text-[13px] font-medium text-text-primary truncate">{displayName}</p>
          {isMe && (
            <span className="text-[9px] font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded shrink-0">You</span>
          )}
          {online && !isMe && (
            <span className="flex items-center gap-1 text-[10px] font-medium text-[var(--color-success)] shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] animate-pulse" />
              Online
            </span>
          )}
        </div>
        <p className="text-[11px] text-text-tertiary truncate">{username || email || member.user_id.slice(0, 8)}</p>
        <div className="flex items-center gap-3 flex-wrap">
          {email && <span className="text-[11px] text-text-secondary truncate max-w-[200px]">{email}</span>}
          <span className={cn('inline-flex text-[10px] font-medium px-2 py-0.5 rounded-full', badge.style)}>
            {badge.label}
          </span>
          {!online && !isMe && (
            <span className="text-[10px] text-text-tertiary/60">Offline</span>
          )}
          <span className="text-[10px] text-text-tertiary/60">{joined}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        {!isMe && (
          <button
            onClick={() => { if (confirm(`Remove ${displayName} from this workspace?`)) onRemove(); }}
            className="p-1.5 text-text-tertiary hover:text-destructive opacity-0 group-hover:opacity-100 transition-all"
            title="Remove member"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold tracking-[0.08em] uppercase text-text-tertiary mb-2.5">
      {children}
    </p>
  );
}
