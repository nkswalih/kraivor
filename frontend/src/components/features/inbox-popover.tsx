'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Inbox, CheckCheck, Loader2, Check } from 'lucide-react';
import { notificationEndpoints, workspaceEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { formatRelativeTime } from '@/lib/utils';

export function InboxPopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const user = useAuthStore(s => s.user);
  const workspaces = useAuthStore(s => s.workspaces);

  const { data: unreadCount } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => notificationEndpoints.unreadCount(),
    refetchInterval: 30_000,
  });

  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications', 'popover'],
    queryFn: () => notificationEndpoints.list(),
    enabled: open,
  });

  // Fetch invitations for all workspaces the user belongs to
  const { data: allInvitations } = useQuery({
    queryKey: ['invitations', 'all'],
    queryFn: async () => {
      const results = await Promise.all(
        (workspaces ?? []).map(w =>
          workspaceEndpoints.listInvitations(w.id).then(invs => ({
            workspaceName: w.name,
            workspaceSlug: w.slug ?? w.id,
            invitations: invs ?? [],
          }))
        )
      );
      return results;
    },
    enabled: open && (workspaces?.length ?? 0) > 0,
  });

  const acceptInviteMut = useMutation({
    mutationFn: (token: string) => workspaceEndpoints.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations', 'all'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const unread = unreadCount?.unread_count ?? 0;
  const recent = (notifications ?? []).slice(0, 3);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-1.5 text-[#A1A1AA] hover:text-[#FAFAFA] transition-colors"
      >
        <Inbox className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-venom-yellow text-[9px] font-bold text-black flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-[380px] bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl z-50 overflow-hidden animate-scale-in origin-top-right">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#27272A]">
            <span className="text-[13px] font-medium text-[#FAFAFA]">Inbox</span>
            {unread > 0 && (
              <button
                onClick={() => {
                  notificationEndpoints.markAllRead().then(() => {
                    queryClient.invalidateQueries({ queryKey: ['notifications'] });
                    queryClient.invalidateQueries({ queryKey: ['unread-count'] });
                  });
                }}
                className="text-[11px] text-venom-yellow hover:text-venom-gold transition-colors flex items-center gap-1"
              >
                <CheckCheck className="w-3 h-3" /> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-[400px] overflow-y-auto">
            {/* Notifications */}
            <div className="px-3 py-2">
              <p className="text-[10px] font-semibold tracking-wider text-text-tertiary uppercase mb-1">
                Notifications
              </p>
              {isLoading ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="w-4 h-4 text-venom-yellow animate-spin" />
                </div>
              ) : recent.length === 0 ? (
                <p className="text-[12px] text-text-tertiary py-2 text-center">No notifications</p>
              ) : (
                <div className="space-y-0.5">
                  {recent.map((n: any) => {
                    const isInvite = n.notification_type === 'workspace.invitation';
                    // Extract token from link like "/invitations/{token}"
                    const token = isInvite && n.link ? n.link.replace('/invitations/', '') : '';
                    return (
                      <div
                        key={n.id}
                        className={`px-3 py-2 rounded-[6px] hover:bg-[#1A1A1D] transition-colors ${
                          n.read_at ? '' : 'bg-[#1A1A1D]/50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p
                              className={`text-[12px] ${n.read_at ? 'text-text-secondary' : 'text-[#FAFAFA] font-medium'}`}
                            >
                              {n.title}
                            </p>
                            {n.body && (
                              <p className="text-[11px] text-text-tertiary mt-0.5 line-clamp-1">
                                {n.body}
                              </p>
                            )}
                            <p className="text-[10px] text-text-tertiary mt-1">
                              {formatRelativeTime(n.created_at)}
                            </p>
                          </div>
                          {isInvite && token && (
                            <button
                              onClick={() =>
                                acceptInviteMut.mutate(token, {
                                  onSuccess: () => {
                                    notificationEndpoints.dismiss(n.id).then(() => {
                                      queryClient.invalidateQueries({
                                        queryKey: ['notifications'],
                                      });
                                      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
                                    });
                                  },
                                })
                              }
                              disabled={acceptInviteMut.isPending}
                              className="shrink-0 px-2.5 py-1 bg-[#6366F1] hover:bg-[#4F46E5] text-white text-[11px] font-medium rounded-[4px] transition-colors disabled:opacity-50 flex items-center gap-1 mt-0.5"
                            >
                              {acceptInviteMut.isPending ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <Check className="w-3 h-3" />
                              )}
                              Accept
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {notifications && notifications.length > 3 && (
                <a
                  href={`/inbox`}
                  className="block text-[11px] text-venom-yellow hover:text-venom-gold text-center py-2 mt-1"
                >
                  View all notifications
                </a>
              )}
            </div>

            {/* Pending Invitations (only where current user is the recipient) */}
            {allInvitations && allInvitations.length > 0 && (
              <div className="px-3 py-2 border-t border-[#27272A]/50">
                <p className="text-[10px] font-semibold tracking-wider text-text-tertiary uppercase mb-1">
                  Pending Invitations
                </p>
                <div className="space-y-1">
                  {allInvitations.map(ws => {
                    const pending = (ws.invitations ?? []).filter(
                      inv => inv.status === 'pending' && inv.email === user?.email
                    );
                    if (pending.length === 0) return null;
                    return pending.map(inv => (
                      <div
                        key={inv.id}
                        className="flex items-center gap-2.5 px-3 py-2 rounded-[6px] hover:bg-[#1A1A1D] transition-colors"
                      >
                        <div className="w-7 h-7 rounded-[4px] bg-[#27272A] flex items-center justify-center text-[10px] font-bold text-[#FAFAFA] shrink-0">
                          {ws.workspaceName.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[12px] font-medium text-[#FAFAFA] truncate">
                            {ws.workspaceName}
                          </p>
                          <p className="text-[10px] text-text-tertiary">Invited as {inv.role}</p>
                        </div>
                        <button
                          onClick={() => acceptInviteMut.mutate(inv.token)}
                          disabled={acceptInviteMut.isPending}
                          className="shrink-0 px-2.5 py-1 bg-[#6366F1] hover:bg-[#4F46E5] text-white text-[11px] font-medium rounded-[4px] transition-colors disabled:opacity-50 flex items-center gap-1"
                        >
                          {acceptInviteMut.isPending ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Check className="w-3 h-3" />
                          )}
                          Accept
                        </button>
                      </div>
                    ));
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
