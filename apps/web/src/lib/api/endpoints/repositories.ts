import { coreApi } from '../client';
import type { Repository, ConnectRepoPayload } from '@/types/api';

export interface GitHubRepo {
  full_name: string;
  name: string;
  owner: string;
  private: boolean;
  description: string;
  language: string | null;
  default_branch: string;
  updated_at: string;
}

export interface InstallAppResponse {
  installation_url: string | null;
  configure_url: string | null;
}

export interface GitHubInstallation {
  id: string;
  installation_id: number;
  github_account_login: string;
  github_account_type: string;
  repositories_synced_at: string | null;
  repos: GitHubRepo[];
}

export interface GitHubInstallationsResponse {
  installations: GitHubInstallation[];
  can_admin: boolean;
}

export const repositoryEndpoints = {
  list: (workspacePk: string) => coreApi.get<Repository[]>(`/workspaces/${workspacePk}/repos/`),

  connect: (workspacePk: string, payload: ConnectRepoPayload) =>
    coreApi.post<Repository>(`/workspaces/${workspacePk}/repos/`, payload),

  disconnect: (workspacePk: string, repoId: string) =>
    coreApi.delete<void>(`/workspaces/${workspacePk}/repos/${repoId}/`),

  listGithubRepos: (workspacePk: string, search?: string) => {
    const query = search?.trim() ? `?search=${encodeURIComponent(search.trim())}` : '';
    return coreApi.get<GitHubRepo[]>(`/workspaces/${workspacePk}/repos/github/${query}`);
  },

  installApp: (workspacePk: string, installationId?: number) => {
    const query = installationId ? `?installation_id=${installationId}` : '';
    return coreApi.get<InstallAppResponse>(
      `/workspaces/${workspacePk}/repos/github/install/${query}`
    );
  },

  listInstallations: (workspacePk: string) =>
    coreApi.get<GitHubInstallationsResponse>(
      `/workspaces/${workspacePk}/repos/github/installations/`
    ),

  importInstallation: (workspacePk: string, installationId: number) =>
    coreApi.post<GitHubInstallation>(
      `/workspaces/${workspacePk}/repos/github/installations/import/`,
      {
        installation_id: installationId,
      }
    ),
};
