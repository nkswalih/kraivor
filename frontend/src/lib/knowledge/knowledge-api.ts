import { coreApi, coreRequest } from '../api/client';
import type { KnowledgeAssetReference } from '@/types/knowledge';

const STRIP_PREFIX = /^knowledge-/;

function stripPrefix(id: string): string {
  return id.replace(STRIP_PREFIX, '');
}

export const knowledgeAssetApi = {
  upload: (knowledgeSpaceId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return coreRequest<KnowledgeAssetReference>(
      `/knowledge/${stripPrefix(knowledgeSpaceId)}/assets/`,
      { method: 'POST', body: form }
    ) as Promise<KnowledgeAssetReference>;
  },

  list: (knowledgeSpaceId: string) =>
    coreApi.get<KnowledgeAssetReference[]>(`/knowledge/${stripPrefix(knowledgeSpaceId)}/assets/`),

  delete: (knowledgeSpaceId: string, assetId: string) =>
    coreApi.delete<void>(`/knowledge/${stripPrefix(knowledgeSpaceId)}/assets/${assetId}/`),
};
