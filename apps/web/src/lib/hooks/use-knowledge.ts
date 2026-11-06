'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeEndpoints } from '@/lib/api/endpoints/knowledge';
import type { KnowledgeSpace } from '@/types/api';

const knowledgeKeys = {
  all: ['knowledge'] as const,
  list: (wsId: string) => [...knowledgeKeys.all, 'list', wsId] as const,
  detail: (id: string) => [...knowledgeKeys.all, 'detail', id] as const,
  versions: (id: string) => [...knowledgeKeys.all, 'versions', id] as const,
};

export function useKnowledgeList(workspaceId: string | undefined, search?: string) {
  return useQuery({
    queryKey: [...knowledgeKeys.list(workspaceId ?? ''), search],
    queryFn: () => knowledgeEndpoints.list(workspaceId!, search),
    enabled: !!workspaceId,
    staleTime: 10_000,
  });
}

export function useKnowledgeDetail(id: string | undefined) {
  return useQuery({
    queryKey: knowledgeKeys.detail(id ?? ''),
    queryFn: () => knowledgeEndpoints.get(id!),
    enabled: !!id,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useCreateKnowledge(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name: string;
      description?: string;
      canvas_data?: Record<string, unknown>;
    }) => knowledgeEndpoints.create(workspaceId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: knowledgeKeys.list(workspaceId) });
    },
  });
}

export function useUpdateKnowledge(id: string, workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name?: string;
      description?: string;
      canvas_data?: Record<string, unknown>;
    }) => knowledgeEndpoints.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: knowledgeKeys.detail(id) });
      qc.invalidateQueries({ queryKey: knowledgeKeys.list(workspaceId) });
    },
  });
}

export function useDeleteKnowledge(id: string, workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => knowledgeEndpoints.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: knowledgeKeys.list(workspaceId) });
    },
  });
}

export function useSaveCanvas(id: string, workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      name: string;
      description?: string;
      canvas_data?: Record<string, unknown>;
    }) => knowledgeEndpoints.update(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: knowledgeKeys.detail(id) });
      qc.invalidateQueries({ queryKey: knowledgeKeys.list(workspaceId) });
    },
  });
}

export function useKnowledgeVersions(id: string) {
  return useQuery({
    queryKey: knowledgeKeys.versions(id),
    queryFn: () => knowledgeEndpoints.getVersions(id),
    enabled: !!id,
  });
}
