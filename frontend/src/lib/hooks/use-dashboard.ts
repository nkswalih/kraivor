'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth-store';
import { workspaceEndpoints } from '@/lib/api/endpoints';
import { chatEndpoints } from '@/lib/api/endpoints';
import { repositoryEndpoints } from '@/lib/api/endpoints';
import { knowledgeEndpoints } from '@/lib/api/endpoints';
import type { Workspace, ChatRoom, Repository, KnowledgeSpace, WorkspaceMember } from '@/types/api';

export interface DashboardData {
  workspace: Workspace | null;
  rooms: ChatRoom[];
  repositories: Repository[];
  knowledgeSpaces: KnowledgeSpace[];
  members: WorkspaceMember[];
  stats: {
    memberCount: number;
    repoCount: number;
    roomCount: number;
    knowledgeCount: number;
    analyzedRepos: number;
  };
}

export function useDashboard() {
  const workspaceId = useAuthStore(s => s.workspaceId);

  const workspaceQuery = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceEndpoints.get(workspaceId!),
    enabled: !!workspaceId,
  });

  const roomsQuery = useQuery({
    queryKey: ['rooms', workspaceId],
    queryFn: () => chatEndpoints.listRooms(workspaceId!),
    enabled: !!workspaceId,
  });

  const reposQuery = useQuery({
    queryKey: ['repos', workspaceId],
    queryFn: () => repositoryEndpoints.list(workspaceId!),
    enabled: !!workspaceId,
  });

  const knowledgeQuery = useQuery({
    queryKey: ['knowledge', workspaceId],
    queryFn: () => knowledgeEndpoints.list(workspaceId!),
    enabled: !!workspaceId,
  });

  const membersQuery = useQuery({
    queryKey: ['members', workspaceId],
    queryFn: () => workspaceEndpoints.getMembers(workspaceId!),
    enabled: !!workspaceId,
  });

  const isLoading =
    workspaceQuery.isLoading ||
    roomsQuery.isLoading ||
    reposQuery.isLoading ||
    knowledgeQuery.isLoading ||
    membersQuery.isLoading;

  const error =
    workspaceQuery.error ||
    roomsQuery.error ||
    reposQuery.error ||
    knowledgeQuery.error ||
    membersQuery.error;

  const workspace = workspaceQuery.data ?? null;
  const rooms = Array.isArray(roomsQuery.data) ? roomsQuery.data : (roomsQuery.data?.results ?? []);
  const repositories = reposQuery.data ?? [];
  const knowledgeSpaces = knowledgeQuery.data ?? [];
  const members = workspace?.members ?? membersQuery.data ?? [];

  const stats = {
    memberCount: workspace?.active_member_count ?? members.length,
    repoCount: repositories.length,
    roomCount: rooms.length,
    knowledgeCount: knowledgeSpaces.length,
    analyzedRepos: repositories.filter(r => r.last_analysis_score != null).length,
  };

  return {
    workspace,
    rooms,
    repositories,
    knowledgeSpaces,
    members,
    stats,
    isLoading,
    error,
    workspaceQuery,
    roomsQuery,
    reposQuery,
    knowledgeQuery,
    membersQuery,
  };
}
