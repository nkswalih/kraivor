import { coreApi } from '../client';
import type {
  Workspace,
  WorkspaceMember,
  WorkspaceInvitation,
  InvitationAcceptResponse,
  CursorPageLegacy,
} from '@/types/api';

export const workspaceEndpoints = {
  list: (pageSize = 20) =>
    coreApi.get<CursorPageLegacy<Workspace>>(`/workspaces/?page_size=${pageSize}`),

  get: (idOrSlug: string) => coreApi.get<Workspace>(`/workspaces/${idOrSlug}/`),

  create: (payload: {
    name: string;
    slug?: string;
    avatar_url?: string;
    description?: string;
    settings?: Record<string, unknown>;
  }) => coreApi.post<Workspace>('/workspaces/', payload),

  update: (
    id: string,
    payload: Partial<Pick<Workspace, 'name' | 'avatar_url' | 'description' | 'settings'>>
  ) => coreApi.patch<Workspace>(`/workspaces/${id}/`, payload),

  delete: (id: string) => coreApi.delete<void>(`/workspaces/${id}/`),

  getMembers: (workspacePk: string) =>
    coreApi.get<WorkspaceMember[]>(`/workspaces/${workspacePk}/members/`),

  inviteMember: (workspacePk: string, payload: { email: string; role?: string }) =>
    coreApi.post<WorkspaceInvitation>(`/workspaces/${workspacePk}/members/invite/`, payload),

  changeMemberRole: (workspacePk: string, userId: string, role: string) =>
    coreApi.patch<WorkspaceMember>(`/workspaces/${workspacePk}/members/${userId}/`, { role }),

  removeMember: (workspacePk: string, userId: string) =>
    coreApi.delete<void>(`/workspaces/${workspacePk}/members/${userId}/`),

  listInvitations: (workspacePk: string) =>
    coreApi.get<WorkspaceInvitation[]>(`/workspaces/${workspacePk}/invitations/`),

  revokeInvitation: (workspacePk: string, invitationId: string) =>
    coreApi.delete<void>(`/workspaces/${workspacePk}/invitations/${invitationId}/`),

  acceptInvitation: (token: string) =>
    coreApi.post<InvitationAcceptResponse>(`/invitations/${token}/accept/`),

  myPendingInvitations: () =>
    coreApi.get<WorkspaceInvitation[]>('/invitations/pending/'),
};
