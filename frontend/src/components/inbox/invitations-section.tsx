'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, Loader2 } from 'lucide-react';
import { workspaceEndpoints } from '@/lib/api/endpoints';
import { InboxCardSkeleton } from './inbox-skeletons';
import { InboxEmpty } from './inbox-shared';
import { usePendingInvites } from './use-inbox-data';

/**
 * Pending invitations, as a single stack.
 *
 * The accept mutation used to invalidate only `['invitations']` from here,
 * which left the badge in the nav rail -- and the unread count -- showing a
 * number the panel had just resolved. It now invalidates the counts too, so
 * the rail drops as the row disappears.
 */
export function InvitationsSection() {
  const queryClient = useQueryClient();
  const { data: pendingInvites, isLoading } = usePendingInvites();

  const acceptMut = useMutation({
    mutationFn: (token: string) => workspaceEndpoints.acceptInvitation(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations', 'all'] });
      queryClient.invalidateQueries({ queryKey: ['invitations', 'mine'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  if (isLoading) return <InboxCardSkeleton rows={3} />;

  if (pendingInvites.length === 0) return <InboxEmpty message="No pending invitations" />;

  return (
    <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4">
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
