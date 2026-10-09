import { coreApi } from '../client';

export interface SearchResultItem {
  id: string;
  type: string;
  title: string;
  description: string;
  url: string;
  workspace_id: string | null;
  relevance: number;
  highlights: Record<string, string[]>;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  page: number;
  page_size: number;
  results: SearchResultItem[];
  facets: Record<string, number>;
}

export const searchEndpoints = {
  search: (query: string, workspaceId: string, scope?: string, signal?: AbortSignal) => {
    let path = `/v1/search/?q=${encodeURIComponent(query)}&workspace=${workspaceId}`;
    if (scope && scope !== 'all') path += `&scope=${scope}`;
    return coreApi.get<SearchResponse>(path, { signal } as RequestInit);
  },
};
