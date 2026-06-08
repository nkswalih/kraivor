import { coreApi } from '../client';
import type { KnowledgeSpace, CreateKnowledgePayload } from '@/types/api';

export const knowledgeEndpoints = {
  list: (workspacePk: string, search?: string) => {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return coreApi.get<KnowledgeSpace[]>(`/workspaces/${workspacePk}/knowledge/${query}`);
  },

  create: (workspacePk: string, payload: CreateKnowledgePayload) =>
    coreApi.post<KnowledgeSpace>(`/workspaces/${workspacePk}/knowledge/`, payload),

  get: (knowledgePk: string) =>
    coreApi.get<KnowledgeSpace>(`/knowledge/${knowledgePk}/`),

  update: (knowledgePk: string, payload: CreateKnowledgePayload) =>
    coreApi.put<KnowledgeSpace>(`/knowledge/${knowledgePk}/`, payload),

  delete: (knowledgePk: string) =>
    coreApi.delete<void>(`/knowledge/${knowledgePk}/`),
};
