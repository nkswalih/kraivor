'use client';

import { useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Check, Trash2, Plus, X, Users, Settings, Mail } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { workspaceEndpoints } from '@/lib/api/endpoints';
import type { WorkspaceMember, WorkspaceInvitation } from '@/types/api';

type Tab = 'settings' | 'team';

export default function WorkspaceSettingsPage() {
  const params = useParams<{ workspace: string }>();
  const currentSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);
  const workspaces = useAuthStore(s => s.workspaces);
  const currentUser = useAuthStore(s => s.user);
  const queryClient = useQueryClient();

  const allWorkspaces = workspaces ?? [];
  const [selectedId, setSelectedId] = useState(workspaceId);
  const [tab, setTab] = useState<Tab>('settings');

  // When topbar switches workspace, update selection
  if (workspaceId && workspaceId !== selectedId) {
    setSelectedId(workspaceId);
  }

  const selected = allWorkspaces.find(w => w.id === selectedId);

  return (
    <div className="flex flex-1 min-h-0 w-full bg-[#0A0A0B] animate-fade-up text-[13px]">
      <div className="flex-1 overflow-y-auto p-8">
        <h1 className="text-xl font-medium text-[#FAFAFA] mb-2">Workspaces</h1>
        <p className="text-[#A1A1AA] mb-6">Manage your workspaces and teams.</p>

        {/* ── Workspace selector pills ────────────────────────── */}
        <div className="flex items-center flex-wrap gap-2 mb-6">
          {allWorkspaces.map(ws => {
            const active = ws.id === selectedId;
            return (
              <button
                key={ws.id}
                onClick={() => {
                  setSelectedId(ws.id);
                  setTab('settings');
                }}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  active
                    ? 'bg-primary text-white shadow-lg shadow-primary/20'
                    : 'bg-[#111113] border border-[#27272A] text-[#A1A1AA] hover:border-[#6366F1]/40 hover:text-[#FAFAFA]'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold shrink-0 ${
                    active ? 'bg-white/20 text-white' : 'bg-[#27272A] text-[#FAFAFA]'
                  }`}
                >
                  {ws.name.charAt(0).toUpperCase()}
                </div>
                {ws.name}
                {ws.id === workspaceId && (
                  <span
                    className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${
                      active ? 'bg-white/20 text-white' : 'bg-[#6366F1]/10 text-[#6366F1]'
                    }`}
                  >
                    Current
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {selected ? (
          <WorkspaceDetail
            key={selected.id}
            workspace={selected}
            isCurrent={selected.id === workspaceId}
            currentUser={currentUser}
            queryClient={queryClient}
            tab={tab}
            onTabChange={setTab}
          />
        ) : (
          <div className="flex items-center justify-center py-20">
            <p className="text-[#A1A1AA]">Select a workspace to manage</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Workspace Detail ───────────────────────────────────────────── */

function WorkspaceDetail({
  workspace,
  isCurrent,
  currentUser,
  queryClient,
  tab,
  onTabChange,
}: {
  workspace: { id: string; name: string; slug: string; description?: string };
  isCurrent: boolean;
  currentUser: { id: string; name: string; email: string } | null;
  queryClient: ReturnType<typeof useQueryClient>;
  tab: Tab;
  onTabChange: (t: Tab) => void;
}) {
  const [name, setName] = useState(workspace.name);
  const [description, setDescription] = useState(workspace.description ?? '');

  const updateMut = useMutation({
    mutationFn: (payload: { name?: string; description?: string }) =>
      workspaceEndpoints.update(workspace.id, payload),
    onSuccess: data => {
      useAuthStore.getState().updateWorkspaceInStore(workspace.id, {
        name: data.name,
        description: data.description ?? undefined,
      });
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });

  const hasChanges = name !== workspace.name || description !== (workspace.description ?? '');

  return (
    <div>
      {/* ── Capsule Tabs ─────────────────────────────────────── */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => onTabChange('settings')}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${
            tab === 'settings'
              ? 'bg-[#27272A] text-[#FAFAFA]'
              : 'text-[#A1A1AA] hover:text-[#FAFAFA]'
          }`}
        >
          <Settings className="w-4 h-4" />
          Settings
        </button>
        <button
          onClick={() => onTabChange('team')}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${
            tab === 'team' ? 'bg-[#27272A] text-[#FAFAFA]' : 'text-[#A1A1AA] hover:text-[#FAFAFA]'
          }`}
        >
          <Users className="w-4 h-4" />
          Team
        </button>
      </div>

      {/* ── Settings Tab ─────────────────────────────────────── */}
      {tab === 'settings' && (
        <div className="max-w-2xl">
          <div className="mb-8">
            <label className="text-sm text-[#A1A1AA] mb-1.5 block">Workspace Name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full bg-[#111113] border border-[#27272A] rounded-xl px-4 py-3 text-[15px] text-[#FAFAFA] focus:outline-none focus:border-[#6366F1] transition-colors"
            />
          </div>

          <div className="mb-8">
            <label className="text-sm text-[#A1A1AA] mb-1.5 block">Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={4}
              className="w-full bg-[#111113] border border-[#27272A] rounded-xl px-4 py-3 text-[15px] text-[#FAFAFA] focus:outline-none focus:border-[#6366F1] transition-colors resize-none"
              placeholder="Describe your workspace..."
            />
          </div>

          <div className="mb-8">
            <label className="text-sm text-[#A1A1AA] mb-1.5 block">Workspace URL</label>
            <div className="flex items-center">
              <span className="bg-[#18181B] border border-[#27272A] border-r-0 rounded-l-xl px-4 py-3 text-sm text-[#A1A1AA]">
                kraivor.com/
              </span>
              <input
                value={workspace.slug}
                disabled
                className="flex-1 bg-[#111113] border border-[#27272A] rounded-r-xl px-4 py-3 text-sm text-[#FAFAFA] opacity-60 cursor-not-allowed"
              />
            </div>
            <p className="text-[11px] text-[#A1A1AA] mt-1.5">
              URL is set on creation and cannot be changed.
            </p>
          </div>

          <div className="flex items-center gap-3 mb-12">
            <button
              onClick={() => updateMut.mutate({ name, description })}
              disabled={updateMut.isPending || !name.trim() || !hasChanges}
              className="bg-primary hover:bg-primary-light text-white font-medium py-2.5 px-6 rounded-xl transition-colors text-sm disabled:opacity-50 flex items-center gap-2"
            >
              {updateMut.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              {updateMut.isPending ? 'Saving...' : 'Save Changes'}
            </button>
            {updateMut.isSuccess && (
              <span className="text-green-400 text-sm flex items-center gap-1">
                <Check className="w-3.5 h-3.5" /> Saved
              </span>
            )}
          </div>

          {/* Danger Zone */}
          {isCurrent && <DangerZone workspaceId={workspace.id} workspaceName={workspace.name} />}
        </div>
      )}

      {/* ── Team Tab ─────────────────────────────────────────── */}
      {tab === 'team' && (
        <TeamSection
          workspaceId={workspace.id}
          currentUser={currentUser}
          queryClient={queryClient}
        />
      )}
    </div>
  );
}

/* ─── Team Section ───────────────────────────────────────────────── */

function TeamSection({
  workspaceId,
  currentUser,
  queryClient,
}: {
  workspaceId: string;
  currentUser: { id: string; name: string; email: string } | null;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [inviteError, setInviteError] = useState('');

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['members', workspaceId],
    queryFn: () => workspaceEndpoints.getMembers(workspaceId),
  });

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
    onError: (err: any) => {
      setInviteError(err?.response?.data?.message || err?.message || 'Invitation failed');
    },
  });

  const removeMemberMut = useMutation({
    mutationFn: (userId: string) => workspaceEndpoints.removeMember(workspaceId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', workspaceId] });
    },
  });

  const changeRoleMut = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      workspaceEndpoints.changeMemberRole(workspaceId, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', workspaceId] });
    },
  });

  const revokeInviteMut = useMutation({
    mutationFn: (invitationId: string) =>
      workspaceEndpoints.revokeInvitation(workspaceId, invitationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations', workspaceId] });
    },
  });

  const membersList: WorkspaceMember[] = members ?? [];
  const allInvitations: WorkspaceInvitation[] = invitationsData ?? [];
  const pendingInvitations = allInvitations.filter(inv => inv.status === 'pending');

  return (
    <div className="max-w-2xl">
      {/* Invite */}
      <div className="flex items-end gap-3 mb-6">
        <div className="flex-1">
          <label className="text-sm text-[#A1A1AA] mb-1.5 block">Invite by email</label>
          <div className="flex items-center gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              placeholder="colleague@company.com"
              className="flex-1 bg-[#111113] border border-[#27272A] rounded-xl px-4 py-2.5 text-sm text-[#FAFAFA] focus:outline-none focus:border-[#6366F1] transition-colors"
            />
            <select
              value={inviteRole}
              onChange={e => setInviteRole(e.target.value)}
              className="bg-[#111113] border border-[#27272A] rounded-xl px-3 py-2.5 text-sm text-[#A1A1AA] focus:outline-none focus:border-[#6366F1]"
            >
              <option value="admin">Admin</option>
              <option value="member">Member</option>
              <option value="viewer">Viewer</option>
            </select>
            <button
              onClick={() => inviteMut.mutate()}
              disabled={!inviteEmail || inviteMut.isPending}
              className="bg-primary hover:bg-primary-light text-white font-medium py-2.5 px-5 rounded-xl transition-colors text-sm disabled:opacity-50 flex items-center gap-1.5 shrink-0"
            >
              {inviteMut.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Mail className="w-4 h-4" />
              )}
              Invite
            </button>
          </div>
        </div>
      </div>
      {inviteError && <p className="text-[12px] text-[#EF4444] -mt-4 mb-4">{inviteError}</p>}

      {/* ── Pending Invitations ──────────────────────────────────── */}
      {invitationsLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="w-4 h-4 animate-spin text-[#A1A1AA]" />
        </div>
      ) : (
        pendingInvitations.length > 0 && (
          <div className="mb-6">
            <p className="text-[10px] font-semibold tracking-wider text-[#A1A1AA] uppercase mb-2">
              Pending Invitations ({pendingInvitations.length})
            </p>
            <div className="space-y-0.5">
              {pendingInvitations.map(inv => (
                <div
                  key={inv.id}
                  className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#18181B]/40 border border-[#27272A]/40 group"
                >
                  <div className="w-8 h-8 rounded-lg bg-[#27272A] flex items-center justify-center text-sm font-bold text-[#FAFAFA] shrink-0">
                    {inv.email.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] text-[#FAFAFA] truncate">{inv.email}</p>
                    <p className="text-[11px] text-[#A1A1AA]">
                      {inv.role} &middot; Expires {new Date(inv.expires_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Revoke invitation for ${inv.email}?`))
                        revokeInviteMut.mutate(inv.id);
                    }}
                    disabled={revokeInviteMut.isPending}
                    className="shrink-0 p-1.5 text-[#A1A1AA] hover:text-[#EF4444] opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )
      )}

      {/* Members */}
      <p className="text-[10px] font-semibold tracking-wider text-[#A1A1AA] uppercase mb-2">
        Members ({membersList.length})
      </p>
      {membersLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-[#A1A1AA]" />
        </div>
      ) : membersList.length === 0 ? (
        <p className="text-sm text-[#A1A1AA] text-center py-8">
          No members yet. Invite someone above.
        </p>
      ) : (
        <div className="space-y-0.5">
          {membersList.map(m => {
            const isMe = m.user_id === currentUser?.id;
            const name =
              m.user?.name ||
              (isMe && currentUser ? currentUser.name : '') ||
              m.user?.email ||
              m.user_id.slice(0, 8);
            const initial = name.charAt(0).toUpperCase();
            return (
              <div
                key={m.id}
                className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-[#18181B] transition-colors group"
              >
                {m.user?.avatar_url ? (
                  <img
                    src={m.user.avatar_url}
                    alt=""
                    className="w-9 h-9 rounded-lg object-cover shrink-0"
                  />
                ) : (
                  <div className="w-9 h-9 rounded-lg bg-[#27272A] flex items-center justify-center text-sm font-bold text-[#FAFAFA] shrink-0">
                    {initial}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-[14px] font-medium text-[#FAFAFA] truncate">{name}</p>
                    {isMe && (
                      <span className="text-[9px] text-primary-light bg-[#6366F1]/10 px-1.5 py-0.5 rounded font-medium">
                        You
                      </span>
                    )}
                  </div>
                </div>
                <select
                  value={m.role}
                  disabled={isMe}
                  onChange={e => changeRoleMut.mutate({ userId: m.user_id, role: e.target.value })}
                  className={`bg-transparent border border-[#27272A] rounded-lg px-2 py-1 text-xs text-[#A1A1AA] focus:outline-none focus:border-[#6366F1] ${isMe ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <option value="owner">Owner</option>
                  <option value="admin">Admin</option>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </select>
                {!isMe && (
                  <button
                    onClick={() => {
                      if (confirm(`Remove ${name}?`)) removeMemberMut.mutate(m.user_id);
                    }}
                    className="p-1.5 text-[#A1A1AA] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ─── Danger Zone ──────────────────────────────────────────────────── */

function DangerZone({
  workspaceId,
  workspaceName,
}: {
  workspaceId: string;
  workspaceName: string;
}) {
  const [confirmDelete, setConfirmDelete] = useState('');

  const deleteMut = useMutation({
    mutationFn: () => workspaceEndpoints.delete(workspaceId),
    onSuccess: () => {
      window.location.href = '/new-workspace';
    },
  });

  return (
    <div className="border border-[#EF4444]/20 rounded-xl p-6">
      <h3 className="text-sm font-medium text-[#EF4444] mb-2">Danger Zone</h3>
      <p className="text-[12px] text-[#A1A1AA] mb-4">
        Once you delete this workspace, there is no going back.
      </p>
      <div className="flex items-center gap-3">
        <input
          value={confirmDelete}
          onChange={e => setConfirmDelete(e.target.value)}
          placeholder={`Type "${workspaceName}" to confirm`}
          className="flex-1 max-w-[360px] bg-[#111113] border border-[#EF4444]/30 rounded-xl px-4 py-2.5 text-sm text-[#FAFAFA] focus:outline-none focus:border-[#EF4444] transition-colors"
        />
        <button
          onClick={() => deleteMut.mutate()}
          disabled={confirmDelete !== workspaceName || deleteMut.isPending}
          className="bg-[#EF4444] hover:bg-[#DC2626] text-white font-medium py-2.5 px-5 rounded-xl transition-colors text-sm disabled:opacity-50 flex items-center gap-2"
        >
          {deleteMut.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
          {deleteMut.isPending ? 'Deleting...' : 'Delete Workspace'}
        </button>
      </div>
    </div>
  );
}
