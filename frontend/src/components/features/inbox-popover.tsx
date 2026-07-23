'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Inbox,
  CheckCheck,
  Loader2,
  Check,
  UserPlus,
  MessageCircle,
  AtSign,
  MessageSquare,
  ThumbsUp,
  FileText,
  GitBranch,
  AlertCircle,
  CheckCircle2,
  Clock,
  Blocks,
} from 'lucide-react';
import { toast } from 'sonner';
import { notificationEndpoints, workspaceEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import { formatRelativeTime } from '@/lib/utils';
import type { Notification } from '@/types/api';

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

  // Fetch my pending invitations across all workspaces
  const { data: myInvitations } = useQuery({
    queryKey: ['invitations', 'mine'],
    queryFn: () => workspaceEndpoints.myPendingInvitations(),
    enabled: open,
  });

  // Fetch per-workspace invitations (admin view, for workspaces the user manages)
  const { data: allInvitations } = useQuery({
    queryKey: ['invitations', 'all'],
    queryFn: async () => {
      const results = await Promise.all(
        (workspaces ?? []).map(w =>
          workspaceEndpoints.listInvitations(w.id).then(invs => ({
            workspaceName: w.name,
            workspaceSlug: w.slug ?? w.id,
            invitations: invs ?? [],
          })).catch(() => ({
            workspaceName: w.name,
            workspaceSlug: w.slug ?? w.id,
            invitations: [],
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
      toast.success('Invitation accepted');
      queryClient.invalidateQueries({ queryKey: ['invitations', 'all'] });
      queryClient.invalidateQueries({ queryKey: ['invitations', 'mine'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to accept invitation');
    },
  });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    const handleInteraction = () => {
      import('@/lib/notification-sound').then(m => m.requestAudioPermission());
    };
    document.addEventListener('click', handleInteraction, { once: true });
    document.addEventListener('touchstart', handleInteraction, { once: true });
    return () => {
      document.removeEventListener('click', handleInteraction);
      document.removeEventListener('touchstart', handleInteraction);
    };
  }, []);

  const unread = unreadCount?.unread_count ?? 0;
  const recent = (notifications ?? []).slice(0, 5);

  const notificationIcon = (type: string) => {
    if (type.startsWith('workspace') || type.startsWith('member')) return UserPlus;
    if (type === 'chat.mention') return AtSign;
    if (type === 'chat.message') return MessageCircle;
    if (type.startsWith('community.discussion')) return MessageSquare;
    if (type.startsWith('community.comment')) return MessageSquare;
    if (type.endsWith('upvoted')) return ThumbsUp;
    if (type.startsWith('project')) return FileText;
    if (type.startsWith('task.assigned')) return UserPlus;
    if (type.startsWith('task.completed')) return CheckCircle2;
    if (type.startsWith('task.blocked')) return Blocks;
    if (type.startsWith('task.overdue')) return Clock;
    if (type.startsWith('task')) return AlertCircle;
    if (type.startsWith('repository')) return GitBranch;
    if (type.startsWith('profile.follow')) return UserPlus;
    if (type.startsWith('analysis.completed')) return CheckCircle2;
    if (type.startsWith('analysis.failed')) return AlertCircle;
    return Inbox;
  };

  const statusBadge = (n: Notification) => {
    const meta = n.metadata;
    if (!meta) return null;
    const status = meta.status as string | undefined;
    const priority = meta.priority as string | undefined;
    if (!status && !priority) return null;
    return (
      <div className="flex gap-1 mt-1 flex-wrap">
        {status && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-[#27272A] text-text-secondary uppercase">
            {status.replace('_', ' ')}
          </span>
        )}
        {priority && (
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium uppercase ${
              priority === 'critical'
                ? 'bg-red-900/40 text-red-400'
                : priority === 'high'
                  ? 'bg-orange-900/40 text-orange-400'
                  : priority === 'medium'
                    ? 'bg-yellow-900/40 text-yellow-400'
                    : 'bg-[#27272A] text-text-secondary'
            }`}
          >
            {priority}
          </span>
        )}
      </div>
    );
  };

  const Icon = notificationIcon(recent[0]?.notification_type || '');

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
                  {recent.map((n) => {
                    const isInvite = n.notification_type === 'workspace.invitation';
                    const isFollow = n.notification_type === 'profile.follow.new';
                    const isUpvote = n.notification_type.endsWith('upvoted');
                    const token = isInvite && n.link ? n.link.replace('/invitations/', '') : '';
                    const Icon = notificationIcon(n.notification_type);
                    const followerUsername = isFollow ? (n.metadata?.follower_username as string) : undefined;
                    return (
                      <div
                        key={n.id}
                        className={`px-3 py-2 rounded-[6px] hover:bg-[#1A1A1D] transition-colors ${
                          n.read_at ? '' : 'bg-[#1A1A1D]/50'
                        }`}
                      >
                        <div className="flex items-start gap-2.5">
                          {isFollow ? (
                            <div className="w-9 h-9 rounded-full bg-venom-yellow flex items-center justify-center shrink-0">
                              <span className="text-sm font-bold text-white">
                                {(followerUsername || 'U').charAt(0).toUpperCase()}
                              </span>
                            </div>
                          ) : isUpvote ? (
                            <div className="w-7 h-7 rounded-full bg-venom-yellow/15 flex items-center justify-center shrink-0 mt-0.5">
                              <ThumbsUp className="w-3.5 h-3.5 text-venom-yellow" />
                            </div>
                          ) : (
                            <div className="w-6 h-6 rounded-full bg-[#27272A] flex items-center justify-center shrink-0 mt-0.5">
                              <Icon className="w-3 h-3 text-text-secondary" />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0 flex-1">
                                {isFollow ? (
                                  <>
                                    <p className="text-[13px] font-semibold text-[#FAFAFA]">
                                      {followerUsername || 'Someone'}
                                    </p>
                                    <p className="text-[11px] text-text-tertiary">Followed you</p>
                                  </>
                                ) : (
                                  <>
                                    <p
                                      className={`text-[12px] leading-tight ${n.read_at ? 'text-text-secondary' : 'text-[#FAFAFA] font-medium'}`}
                                    >
                                      {n.title}
                                    </p>
                                    {n.body && (
                                      <p className="text-[11px] text-text-tertiary mt-0.5 line-clamp-1">
                                        {n.body}
                                      </p>
                                    )}
                                  </>
                                )}
                                {statusBadge(n)}
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
                                          queryClient.invalidateQueries({
                                            queryKey: ['unread-count'],
                                          });
                                        });
                                      },
                                    })
                                  }
                                  disabled={acceptInviteMut.isPending}
                                  className="shrink-0 px-2.5 py-1 bg-venom-yellow hover:bg-venom-gold text-black text-[11px] font-medium rounded-[4px] transition-colors disabled:opacity-50 flex items-center gap-1 mt-0.5"
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
            {myInvitations && myInvitations.length > 0 && (
              <div className="px-3 py-2 border-t border-[#27272A]/50">
                <p className="text-[10px] font-semibold tracking-wider text-text-tertiary uppercase mb-1">
                  Pending Invitations
                </p>
                <div className="space-y-1">
                  {myInvitations.map(inv => (
                    <div
                      key={inv.id}
                      className="flex items-center gap-2.5 px-3 py-2 rounded-[6px] hover:bg-[#1A1A1D] transition-colors"
                    >
                      <div className="w-7 h-7 rounded-[4px] bg-[#27272A] flex items-center justify-center text-[10px] font-bold text-[#FAFAFA] shrink-0">
                        {(inv.workspace_name ?? 'W').charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-medium text-[#FAFAFA] truncate">
                          {inv.workspace_name}
                        </p>
                        <p className="text-[10px] text-text-tertiary">Invited as {inv.role}</p>
                      </div>
                      <button
                        onClick={() => acceptInviteMut.mutate(inv.token)}
                        disabled={acceptInviteMut.isPending}
                        className="shrink-0 px-2.5 py-1 bg-venom-yellow hover:bg-venom-gold text-black text-[11px] font-medium rounded-[4px] transition-colors disabled:opacity-50 flex items-center gap-1"
                      >
                        {acceptInviteMut.isPending ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Check className="w-3 h-3" />
                        )}
                        Accept
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
