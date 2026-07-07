'use client';

import { useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Check, Trash2, Settings, Users, Mail } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { workspaceEndpoints, profileEndpoints } from '@/lib/api/endpoints';
import type { WorkspaceMember, WorkspaceInvitation } from '@/types/api';
import { cn } from '@/lib/utils';

type Tab = 'settings' | 'team';

export function WorkspaceView() {
  const params = useParams<{ workspace: string }>();
  const currentSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);
  const workspaces = useAuthStore(s => s.workspaces);
  const currentUser = useAuthStore(s => s.user);

  const allWorkspaces = workspaces ?? [];
  const [selectedId, setSelectedId] = useState(workspaceId);
  const [tab, setTab] = useState<Tab>('settings');

  // When topbar switches workspace, update selection
  if (workspaceId && workspaceId !== selectedId) {
    setSelectedId(workspaceId);
  }

  const selected = allWorkspaces.find(w => w.id === selectedId);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">Workspace</h2>
        <p className="text-[12px] text-text-secondary mt-1">
          Manage your workspace settings and team.
        </p>
      </div>

      {/* Workspace Pills */}
      <div className="flex items-center flex-wrap gap-2">
        {allWorkspaces.map(ws => {
          const active = ws.id === selectedId;
          return (
            <button
              key={ws.id}
              onClick={() => { setSelectedId(ws.id); setTab('settings'); }}
              className={cn(
                'inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[12px] font-medium transition-all duration-150',
                  active
                    ? 'bg-primary/20 text-text-primary border border-primary/30'
                    : 'bg-krait-surface-1 border border-krait-border text-text-secondary hover:border-krait-border-hi hover:text-text-secondary'
              )}
            >
              <div className={cn(
                'w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold shrink-0',
                active ? 'bg-primary/30 text-text-primary' : 'bg-muted text-text-secondary'
              )}>
                {ws.name.charAt(0).toUpperCase()}
              </div>
              {ws.name}
              {ws.id === workspaceId && (
                <span className={cn(
                  'text-[9px] font-medium px-1.5 py-0.5 rounded-full',
                  active ? 'bg-white/10 text-white' : 'bg-primary/10 text-primary'
                )}>
                  Current
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Capsule Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setTab('settings')}
          className={cn(
            'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-[12px] font-medium transition-all duration-150',
            tab === 'settings'
              ? 'bg-muted text-text-primary'
              : 'text-text-tertiary hover:text-text-secondary'
          )}
        >
          <Settings className="w-3.5 h-3.5" />
          Settings
        </button>
        <button
          onClick={() => setTab('team')}
          className={cn(
            'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-[12px] font-medium transition-all duration-150',
            tab === 'team'
              ? 'bg-muted text-text-primary'
              : 'text-text-tertiary hover:text-text-secondary'
          )}
        >
          <Users className="w-3.5 h-3.5" />
          Team
        </button>
      </div>

      {selected ? (
        <WorkspaceDetailContent
          key={selected.id}
          workspace={selected}
          isCurrent={selected.id === workspaceId}
          tab={tab}
        />
      ) : (
        <div className="flex items-center justify-center py-20">
          <p className="text-[13px] text-text-tertiary">Select a workspace to manage</p>
        </div>
      )}
    </div>
  );
}

function WorkspaceDetailContent({
  workspace,
  isCurrent,
  tab,
}: {
  workspace: { id: string; name: string; slug: string; description?: string };
  isCurrent: boolean;
  tab: Tab;
}) {
  const [name, setName] = useState(workspace?.name ?? '');
  const [description, setDescription] = useState(workspace.description ?? '');
  const queryClient = useQueryClient();

  const updateMut = useMutation({
    mutationFn: (payload: { name?: string; description?: string }) =>
      workspaceEndpoints.update(workspace?.id ?? '', payload),
    onSuccess: data => {
      useAuthStore.getState().updateWorkspaceInStore(workspace?.id ?? '', {
        name: data.name,
        description: data.description ?? undefined,
      });
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });

  const hasChanges = name !== (workspace?.name ?? '') || description !== (workspace?.description ?? '');

  if (tab === 'settings') {
    return (
      <div className="max-w-[560px] space-y-6">
        <div>
          <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Workspace Name</label>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full bg-krait-surface-1 border border-krait-border rounded-lg px-3.5 py-2.5 text-[14px] text-text-primary focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Description</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={3}
            className="w-full bg-krait-surface-1 border border-krait-border rounded-lg px-3.5 py-2.5 text-[14px] text-text-primary focus:outline-none focus:border-primary transition-colors resize-none"
          />
        </div>

        <div>
          <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Workspace URL</label>
          <div className="flex items-center">
            <span className="bg-muted border border-krait-border border-r-0 rounded-l-lg px-3.5 py-2.5 text-[13px] text-text-tertiary">
              kraivor.com/
            </span>
            <input
              value={workspace?.slug ?? ''}
              disabled
              className="flex-1 bg-krait-surface-1 border border-krait-border rounded-r-lg px-3.5 py-2.5 text-[13px] text-text-primary opacity-50 cursor-not-allowed"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => updateMut.mutate({ name, description })}
            disabled={updateMut.isPending || !name.trim() || !hasChanges}
            className="bg-primary hover:bg-primary-dark text-primary-foreground font-medium py-2 px-5 rounded-lg transition-all duration-150 text-[13px] disabled:opacity-40 flex items-center gap-2 active:scale-[0.98]"
          >
            {updateMut.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
            {updateMut.isPending ? 'Saving...' : 'Save Changes'}
          </button>
          {updateMut.isSuccess && (
            <span className="text-[12px] text-[var(--color-success)] flex items-center gap-1">
              <Check className="w-3 h-3" /> Saved
            </span>
          )}
        </div>

        {isCurrent && <DangerZoneContent workspaceId={workspace?.id ?? ''} workspaceName={workspace?.name ?? ''} />}
      </div>
    );
  }

  if (tab === 'team') {
    return <TeamContent workspaceId={workspace?.id ?? ''} />;
  }

  return null;
}

function TeamContent({ workspaceId }: { workspaceId: string }) {
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [inviteError, setInviteError] = useState('');
  const queryClient = useQueryClient();
  const currentUser = useAuthStore(s => s.user);

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['members', workspaceId],
    queryFn: () => workspaceEndpoints.getMembers(workspaceId),
  });

  const memberIds = useMemo(() => (members ?? []).map(m => m.user_id), [members]);

  const { data: profilesData } = useQuery({
    queryKey: ['profiles-by-ids', memberIds],
    queryFn: () => profileEndpoints.getProfilesByIds(memberIds),
    enabled: memberIds.length > 0,
    staleTime: 60_000,
  });

  const profileMap = useMemo(() => profilesData?.profiles ?? {}, [profilesData]);

  const { data: invitationsData, isLoading: invitationsLoading } = useQuery({
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
    onError: (err: unknown) => {
      setInviteError(err instanceof Error ? err.message : 'Invitation failed');
    },
  });

  const removeMemberMut = useMutation({
    mutationFn: (userId: string) => workspaceEndpoints.removeMember(workspaceId, userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['members', workspaceId] }),
  });

  const changeRoleMut = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      workspaceEndpoints.changeMemberRole(workspaceId, userId, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['members', workspaceId] }),
  });

  const revokeInviteMut = useMutation({
    mutationFn: (invitationId: string) =>
      workspaceEndpoints.revokeInvitation(workspaceId, invitationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations', workspaceId] }),
  });

  const allMembers: WorkspaceMember[] = members ?? [];
  const allInvitations: WorkspaceInvitation[] = invitationsData ?? [];
  const pendingInvitations = allInvitations.filter(inv => inv.status === 'pending');

  return (
    <div className="max-w-[560px] space-y-6">
      {/* Invite */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Invite by email</label>
          <div className="flex items-center gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              placeholder="colleague@company.com"
              className="flex-1 bg-krait-surface-1 border border-krait-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors"
            />
            <select
              value={inviteRole}
              onChange={e => setInviteRole(e.target.value)}
              className="bg-krait-surface-1 border border-krait-border rounded-lg px-2.5 py-2 text-[12px] text-text-secondary focus:outline-none focus:border-primary"
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
           className="bg-primary hover:bg-primary-dark text-primary-foreground font-medium py-2 px-4 rounded-lg transition-all duration-150 text-[12px] disabled:opacity-40 flex items-center gap-1.5 shrink-0 active:scale-[0.98]"
        >
          {inviteMut.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Mail className="w-3 h-3" />}
          Invite
        </button>
      </div>
      {inviteError && <p className="text-[12px] text-destructive -mt-4">{inviteError}</p>}

      {/* Pending Invitations */}
      {invitationsLoading ? (
        <div className="flex justify-center py-4"><Loader2 className="w-4 h-4 animate-spin text-text-tertiary" /></div>
      ) : pendingInvitations.length > 0 ? (
        <div>
          <p className="text-[10px] font-semibold tracking-wider text-text-tertiary uppercase mb-2">
            Pending Invitations ({pendingInvitations.length})
          </p>
          <div className="space-y-0.5">
            {pendingInvitations.map(inv => (
              <div key={inv.id} className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg bg-krait-surface-1 border border-krait-border group">
                <div className="w-7 h-7 rounded bg-muted flex items-center justify-center text-xs font-bold text-text-secondary shrink-0">
                  {inv.email.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] text-text-primary truncate">{inv.email}</p>
                  <p className="text-[11px] text-text-tertiary">{inv.role} &middot; Expires {new Date(inv.expires_at).toLocaleDateString()}</p>
                </div>
                <button
                  onClick={() => { if (confirm(`Revoke invitation for ${inv.email}?`)) revokeInviteMut.mutate(inv.id); }}
                  disabled={revokeInviteMut.isPending}
                      className="p-1 text-text-tertiary hover:text-destructive opacity-0 group-hover:opacity-100 transition-all"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Members */}
      <div>
        <p className="text-[10px] font-semibold tracking-wider text-text-tertiary uppercase mb-2">
          Members ({allMembers.length})
        </p>
        {membersLoading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-text-tertiary" /></div>
        ) : allMembers.length === 0 ? (
          <p className="text-[13px] text-text-tertiary text-center py-8">No members yet.</p>
        ) : (
          <div className="space-y-0.5">
            {allMembers.map(m => {
              const isMe = m.user_id === currentUser?.id;
              const profile = profileMap[m.user_id];
              const displayName = profile?.display_name ?? profile?.username ?? m.user?.name ?? (isMe && currentUser ? currentUser.name : '') ?? m.user_id.slice(0, 8);
              const avatarSrc = profile?.avatar_url ?? profile?.user_avatar_url ?? m.user?.avatar_url ?? null;
              const initials = displayName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
              return (
                <div key={m.id} className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg hover:bg-krait-surface-1 transition-colors group border border-transparent hover:border-krait-border">
                  {avatarSrc ? (
                    <img src={avatarSrc} alt="" loading="lazy" className="w-8 h-8 rounded object-cover shrink-0" />
                  ) : (
                    <div className="w-8 h-8 rounded bg-muted flex items-center justify-center text-xs font-bold text-text-secondary shrink-0">{initials}</div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-[13px] font-medium text-text-primary truncate">{displayName}</p>
                      {isMe && <span className="text-[9px] text-primary bg-primary/10 px-1.5 py-0.5 rounded font-medium">You</span>}
                    </div>
                  </div>
                  <select
                    value={m.role}
                    disabled={isMe}
                    onChange={e => changeRoleMut.mutate({ userId: m.user_id, role: e.target.value })}
                    className={cn(
                      'bg-transparent border border-krait-border rounded px-2 py-1 text-[11px] text-text-secondary focus:outline-none focus:border-primary',
                      isMe && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <option value="owner">Owner</option>
                    <option value="admin">Admin</option>
                    <option value="member">Member</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  {!isMe && (
                    <button
                      onClick={() => { if (confirm(`Remove ${displayName}?`)) removeMemberMut.mutate(m.user_id); }}
                  className="p-1 text-text-tertiary hover:text-destructive opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function DangerZoneContent({ workspaceId, workspaceName }: { workspaceId: string; workspaceName: string }) {
  const [confirmDelete, setConfirmDelete] = useState('');
  const deleteMut = useMutation({
    mutationFn: () => workspaceEndpoints.delete(workspaceId),
    onSuccess: () => { window.location.href = '/new-workspace'; },
  });

  return (
    <div className="border border-destructive/20 rounded-xl p-5 mt-8">
      <h3 className="text-sm font-medium text-destructive mb-1">Danger Zone</h3>
      <p className="text-[12px] text-text-tertiary mb-4">Once you delete this workspace, there is no going back.</p>
      <div className="flex items-center gap-3">
        <input
          value={confirmDelete}
          onChange={e => setConfirmDelete(e.target.value)}
          placeholder={`Type "${workspaceName}" to confirm`}
          className="flex-1 max-w-[360px] bg-krait-surface-1 border border-destructive/30 rounded-lg px-3.5 py-2 text-[13px] text-text-primary focus:outline-none focus:border-destructive transition-colors"
        />
        <button
          onClick={() => deleteMut.mutate()}
          disabled={confirmDelete !== workspaceName || deleteMut.isPending}
          className="bg-destructive hover:bg-destructive/90 text-white font-medium py-2 px-5 rounded-lg transition-all duration-150 text-[13px] disabled:opacity-40 flex items-center gap-2 active:scale-[0.98]"
        >
          {deleteMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
          {deleteMut.isPending ? 'Deleting...' : 'Delete Workspace'}
        </button>
      </div>
    </div>
  );
}
