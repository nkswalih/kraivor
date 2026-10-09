import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { notificationEndpoints, workspaceEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';
import type { PendingInvite } from './inbox-shared';

/**
 * The three reads the panel is built on, shared by the nav rail and the
 * sections.
 *
 * They live in one place because both halves need them and React Query only
 * dedupes by key: the rail asks for unread count, notifications and invites to
 * draw its badges, and three of the five sections then ask for the same
 * things. With one definition those are cache hits rather than a second
 * request, which is what makes switching sections feel free. Two definitions
 * with the same logic and a typo'd key would silently double the traffic.
 *
 * The keys are the ones the app already uses elsewhere (`['unread-count']` in
 * the topbar, `['invitations', 'mine']` in the popover), so opening the panel
 * inherits whatever has already been fetched.
 */

export function useUnreadCount() {
  return useQuery({
    queryKey: ['unread-count'],
    queryFn: () => notificationEndpoints.unreadCount(),
    refetchInterval: 30_000,
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationEndpoints.list(),
  });
}

/**
 * Pending invitations for the current user.
 *
 * Two sources, deliberately: `/invitations/pending/` works for anyone, and the
 * per-workspace listing is the fallback for users who manage workspaces. The
 * second is a fan-out across every workspace, so it is disabled outright when
 * there are none rather than left to resolve as an empty request.
 */
export function usePendingInvites(): { data: PendingInvite[]; isLoading: boolean } {
  const user = useAuthStore(s => s.user);
  const workspaces = useAuthStore(s => s.workspaces);
  const hasWorkspaces = (workspaces?.length ?? 0) > 0;

  const { data: myInvitationsData, isLoading: loadingMine } = useQuery({
    queryKey: ['invitations', 'mine'],
    queryFn: () => workspaceEndpoints.myPendingInvitations(),
  });

  const { data: allInvitationsData, isLoading: loadingAll } = useQuery({
    queryKey: ['invitations', 'all'],
    queryFn: async () => {
      const results = await Promise.all(
        (workspaces ?? []).map(w =>
          workspaceEndpoints
            .listInvitations(w.id)
            .then(invs => ({
              workspaceId: w.id,
              workspaceName: w.name,
              invitations: invs ?? [],
            }))
            .catch(() => ({
              workspaceId: w.id,
              workspaceName: w.name,
              invitations: [] as Awaited<ReturnType<typeof workspaceEndpoints.listInvitations>>,
            }))
        )
      );
      return results;
    },
    enabled: hasWorkspaces,
  });

  const data = useMemo(() => {
    const items: PendingInvite[] = [];
    const seen = new Set<string>();
    // Primary source: /invitations/pending/ endpoint (works for all users)
    for (const inv of myInvitationsData ?? []) {
      const token = inv.token;
      if (!seen.has(token)) {
        seen.add(token);
        items.push({
          id: inv.id,
          // `WorkspaceInvitation.workspace_name` is always present: the
          // serializer sources it from a non-nullable FK to a non-null
          // CharField, so a `?? 'Unknown'` fallback would be unreachable.
          workspaceName: inv.workspace_name,
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

  return { data, isLoading: loadingMine || (loadingAll && hasWorkspaces) };
}
