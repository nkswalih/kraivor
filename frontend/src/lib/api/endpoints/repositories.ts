import { coreApi } from '../client';
import type { Repository, ConnectRepoPayload } from '@/types/api';

export const repositoryEndpoints = {
  list: (workspacePk: string) =>
    coreApi.get<Repository[]>(`/workspaces/${workspacePk}/repos/`),

  connect: (workspacePk: string, payload: ConnectRepoPayload) =>
    coreApi.post<Repository>(`/workspaces/${workspacePk}/repos/`, payload),

  disconnect: (workspacePk: string, repoId: string) =>
    coreApi.delete<void>(`/workspaces/${workspacePk}/repos/${repoId}/`),
};
