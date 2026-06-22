'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  projectEndpoints,
  taskEndpoints,
  repositoryEndpoints,
  knowledgeEndpoints,
} from '@/lib/api/endpoints';
import type {
  ProjectCreatePayload,
  ProjectUpdatePayload,
  TaskCreatePayload,
  TaskUpdatePayload,
  TaskStatusUpdatePayload,
  ProjectStatus,
  TaskStatus,
  TaskPriority,
} from '@/types/domain/projects';

export const projectKeys = {
  all: (wsId: string) => ['projects', wsId] as const,
  list: (wsId: string, status?: ProjectStatus) =>
    [...projectKeys.all(wsId), 'list', status] as const,
  detail: (wsId: string, id: string) => [...projectKeys.all(wsId), 'detail', id] as const,
  tasks: (wsId: string, projectId: string) =>
    [...projectKeys.all(wsId), 'tasks', projectId] as const,
  ai: (wsId: string, projectId: string) => [...projectKeys.all(wsId), 'ai', projectId] as const,
};

export const taskKeys = {
  all: (wsId: string) => ['tasks', wsId] as const,
  list: (wsId: string, filters?: object) => [...taskKeys.all(wsId), 'list', filters] as const,
  detail: (wsId: string, id: string) => [...taskKeys.all(wsId), 'detail', id] as const,
};

export function useProjects(workspaceId: string, status?: ProjectStatus) {
  return useQuery({
    queryKey: projectKeys.list(workspaceId, status),
    queryFn: () => projectEndpoints.list(workspaceId, status ? { status } : undefined),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });
}

export function useProject(workspaceId: string, projectId: string) {
  return useQuery({
    queryKey: projectKeys.detail(workspaceId, projectId),
    queryFn: () => projectEndpoints.get(workspaceId, projectId),
    enabled: !!workspaceId && !!projectId,
    staleTime: 30_000,
  });
}

export function useCreateProject(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProjectCreatePayload) => projectEndpoints.create(workspaceId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.all(workspaceId) });
    },
  });
}

export function useUpdateProject(workspaceId: string, projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProjectUpdatePayload) =>
      projectEndpoints.update(workspaceId, projectId, payload),
    onSuccess: updated => {
      qc.setQueryData(projectKeys.detail(workspaceId, projectId), updated);
      qc.invalidateQueries({ queryKey: projectKeys.list(workspaceId) });
    },
  });
}

export function useDeleteProject(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => projectEndpoints.delete(workspaceId, projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectKeys.all(workspaceId) });
    },
  });
}

export function useProjectTasks(
  workspaceId: string,
  projectId: string,
  filters?: { status?: TaskStatus; priority?: TaskPriority }
) {
  return useQuery({
    queryKey: projectKeys.tasks(workspaceId, projectId),
    queryFn: () => taskEndpoints.listForProject(workspaceId, projectId, filters),
    enabled: !!workspaceId && !!projectId,
    staleTime: 15_000,
  });
}

export function useTasks(
  workspaceId: string,
  filters?: {
    project_id?: string;
    status?: TaskStatus;
    assignee_id?: string;
    priority?: TaskPriority;
  }
) {
  return useQuery({
    queryKey: taskKeys.list(workspaceId, filters),
    queryFn: () => taskEndpoints.list(workspaceId, filters),
    enabled: !!workspaceId,
    staleTime: 15_000,
  });
}

export function useTask(workspaceId: string, taskId: string) {
  return useQuery({
    queryKey: taskKeys.detail(workspaceId, taskId),
    queryFn: () => taskEndpoints.get(workspaceId, taskId),
    enabled: !!workspaceId && !!taskId,
    staleTime: 15_000,
  });
}

export function useCreateTask(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaskCreatePayload) => taskEndpoints.create(workspaceId, payload),
    onSuccess: task => {
      qc.invalidateQueries({ queryKey: taskKeys.all(workspaceId) });
      qc.invalidateQueries({
        queryKey: projectKeys.tasks(workspaceId, task.project_id),
      });
    },
  });
}

export function useUpdateTask(workspaceId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaskUpdatePayload) => taskEndpoints.update(workspaceId, taskId, payload),
    onSuccess: updated => {
      qc.setQueryData(taskKeys.detail(workspaceId, taskId), updated);
      qc.invalidateQueries({ queryKey: taskKeys.all(workspaceId) });
    },
  });
}

export function useUpdateTaskStatus(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: TaskStatusUpdatePayload }) =>
      taskEndpoints.updateStatus(workspaceId, taskId, payload),
    onSuccess: updated => {
      qc.setQueryData(taskKeys.detail(workspaceId, updated.id), updated);
      qc.invalidateQueries({ queryKey: taskKeys.all(workspaceId) });
      qc.invalidateQueries({
        queryKey: projectKeys.tasks(workspaceId, updated.project_id),
      });
    },
  });
}

export function useDeleteTask(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => taskEndpoints.delete(workspaceId, taskId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.all(workspaceId) });
    },
  });
}

export function useRepositoriesList(workspaceId: string) {
  return useQuery({
    queryKey: ['repositories', workspaceId],
    queryFn: () => repositoryEndpoints.list(workspaceId),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });
}

export function useKnowledgeSpacesList(workspaceId: string) {
  return useQuery({
    queryKey: ['knowledgeSpaces', workspaceId],
    queryFn: () => knowledgeEndpoints.list(workspaceId),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });
}

export function useTaskSearch(workspaceId: string, search: string) {
  return useQuery({
    queryKey: ['taskSearch', workspaceId, search],
    queryFn: () => taskEndpoints.list(workspaceId, { page: 1 }),
    enabled: !!workspaceId && search.length > 0,
    staleTime: 10_000,
  });
}

export function useAddDependency(workspaceId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: import('@/types/domain/projects').AddDependencyPayload) =>
      taskEndpoints.addDependency(workspaceId, taskId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.detail(workspaceId, taskId) });
    },
  });
}

export function useRemoveDependency(workspaceId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dependencyId: string) =>
      taskEndpoints.removeDependency(workspaceId, taskId, dependencyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.detail(workspaceId, taskId) });
    },
  });
}

export function useLinkRepository(workspaceId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (repositoryId: string) =>
      taskEndpoints.linkRepository(workspaceId, taskId, repositoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.detail(workspaceId, taskId) });
    },
  });
}

export function useRemoveLinkRepository(workspaceId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (linkId: string) => taskEndpoints.removeLinkRepository(workspaceId, taskId, linkId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.detail(workspaceId, taskId) });
    },
  });
}

export function useRemoveLinkKnowledge(workspaceId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (linkId: string) => taskEndpoints.removeLinkKnowledge(workspaceId, taskId, linkId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.detail(workspaceId, taskId) });
    },
  });
}

export function useLinkKnowledge(workspaceId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (knowledgeSpaceId: string) =>
      taskEndpoints.linkKnowledge(workspaceId, taskId, knowledgeSpaceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.detail(workspaceId, taskId) });
    },
  });
}

export function useAIRecommendations(workspaceId: string, projectId: string) {
  return useQuery({
    queryKey: projectKeys.ai(workspaceId, projectId),
    queryFn: () => projectEndpoints.aiRecommendations(workspaceId, projectId),
    enabled: !!workspaceId && !!projectId,
    staleTime: 120_000,
  });
}
