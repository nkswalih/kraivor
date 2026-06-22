import { coreApi } from '../client';
import type {
  Project,
  ProjectCreatePayload,
  ProjectUpdatePayload,
  Task,
  TaskCreatePayload,
  TaskUpdatePayload,
  TaskStatusUpdatePayload,
  AddDependencyPayload,
  PaginatedResponse,
  AIRecommendations,
  ProjectStatus,
  TaskStatus,
  TaskPriority,
} from '@/types/domain/projects';

export const projectEndpoints = {
  list: (workspaceId: string, params?: { status?: ProjectStatus }) => {
    if (params?.status) {
      return coreApi.get<Project[]>(`/workspaces/${workspaceId}/projects/?status=${params.status}`);
    }
    return coreApi.get<Project[]>(`/workspaces/${workspaceId}/projects/`);
  },

  create: (workspaceId: string, payload: ProjectCreatePayload) =>
    coreApi.post<Project>(`/workspaces/${workspaceId}/projects/`, payload),

  get: (workspaceId: string, projectId: string) =>
    coreApi.get<Project>(`/workspaces/${workspaceId}/projects/${projectId}/`),

  update: (workspaceId: string, projectId: string, payload: ProjectUpdatePayload) =>
    coreApi.patch<Project>(`/workspaces/${workspaceId}/projects/${projectId}/`, payload),

  delete: (workspaceId: string, projectId: string) =>
    coreApi.delete<void>(`/workspaces/${workspaceId}/projects/${projectId}/`),

  aiRecommendations: (workspaceId: string, projectId: string) =>
    coreApi.get<AIRecommendations>(
      `/workspaces/${workspaceId}/projects/${projectId}/ai/recommendations/`
    ),
};

export const taskEndpoints = {
  list: (
    workspaceId: string,
    params?: {
      project_id?: string;
      status?: TaskStatus;
      assignee_id?: string;
      priority?: TaskPriority;
      page?: number;
    }
  ) => {
    const qs = new URLSearchParams();
    if (params?.project_id) qs.set('project_id', params.project_id);
    if (params?.status) qs.set('status', params.status);
    if (params?.assignee_id) qs.set('assignee_id', params.assignee_id);
    if (params?.priority) qs.set('priority', params.priority);
    if (params?.page) qs.set('page', String(params.page));
    const query = qs.toString();
    return coreApi.get<PaginatedResponse<Task>>(
      `/workspaces/${workspaceId}/tasks/${query ? `?${query}` : ''}`
    );
  },

  listForProject: (
    workspaceId: string,
    projectId: string,
    params?: { status?: TaskStatus; assignee_id?: string; priority?: TaskPriority }
  ) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.assignee_id) qs.set('assignee_id', params.assignee_id);
    if (params?.priority) qs.set('priority', params.priority);
    const query = qs.toString();
    return coreApi.get<PaginatedResponse<Task>>(
      `/workspaces/${workspaceId}/projects/${projectId}/tasks/${query ? `?${query}` : ''}`
    );
  },

  create: (workspaceId: string, payload: TaskCreatePayload) =>
    coreApi.post<Task>(`/workspaces/${workspaceId}/tasks/`, payload),

  get: (workspaceId: string, taskId: string) =>
    coreApi.get<Task>(`/workspaces/${workspaceId}/tasks/${taskId}/`),

  update: (workspaceId: string, taskId: string, payload: TaskUpdatePayload) =>
    coreApi.patch<Task>(`/workspaces/${workspaceId}/tasks/${taskId}/`, payload),

  updateStatus: (workspaceId: string, taskId: string, payload: TaskStatusUpdatePayload) =>
    coreApi.patch<Task>(`/workspaces/${workspaceId}/tasks/${taskId}/status/`, payload),

  delete: (workspaceId: string, taskId: string) =>
    coreApi.delete<void>(`/workspaces/${workspaceId}/tasks/${taskId}/`),

  addDependency: (workspaceId: string, taskId: string, payload: AddDependencyPayload) =>
    coreApi.post<{ id: string; relationship_type: string }>(
      `/workspaces/${workspaceId}/tasks/${taskId}/dependencies/`,
      payload
    ),

  removeDependency: (workspaceId: string, taskId: string, dependencyId: string) =>
    coreApi.delete<void>(
      `/workspaces/${workspaceId}/tasks/${taskId}/dependencies/${dependencyId}/`
    ),

  linkRepository: (workspaceId: string, taskId: string, repositoryId: string) =>
    coreApi.post<{ id: string; repository_id: string }>(
      `/workspaces/${workspaceId}/tasks/${taskId}/repositories/`,
      { repository_id: repositoryId }
    ),

  removeLinkRepository: (workspaceId: string, taskId: string, linkId: string) =>
    coreApi.delete<void>(`/workspaces/${workspaceId}/tasks/${taskId}/repositories/${linkId}/`),

  linkKnowledge: (workspaceId: string, taskId: string, knowledgeSpaceId: string) =>
    coreApi.post<{ id: string; knowledge_space_id: string }>(
      `/workspaces/${workspaceId}/tasks/${taskId}/knowledge/`,
      { knowledge_space_id: knowledgeSpaceId }
    ),

  removeLinkKnowledge: (workspaceId: string, taskId: string, linkId: string) =>
    coreApi.delete<void>(`/workspaces/${workspaceId}/tasks/${taskId}/knowledge/${linkId}/`),
};
