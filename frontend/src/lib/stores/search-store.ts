import { create } from 'zustand';
import {
  searchEndpoints,
  type SearchResultItem,
  type SearchResponse,
} from '@/lib/api/endpoints/search';

interface CacheEntry {
  results: SearchResultItem[];
  facets: Record<string, number>;
  total: number;
  timestamp: number;
}

const CACHE_TTL = 30_000;
const MAX_CACHE = 50;

interface SearchStore {
  query: string;
  results: SearchResultItem[];
  facets: Record<string, number>;
  totalResults: number;
  isLoading: boolean;
  error: string | null;
  scope: string;
  cache: Map<string, CacheEntry>;

  setQuery: (q: string) => void;
  setScope: (s: string) => void;
  clearSearch: () => void;
  executeSearch: (query: string, workspaceId: string) => Promise<void>;
  cancelSearch: () => void;
}

let activeController: AbortController | null = null;

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === 'AbortError';
}

export const useSearchStore = create<SearchStore>((set, get) => ({
  query: '',
  results: [],
  facets: {},
  totalResults: 0,
  isLoading: false,
  error: null,
  scope: 'all',
  cache: new Map(),

  setQuery: q => set({ query: q }),
  setScope: s => set({ scope: s }),

  clearSearch: () => {
    if (activeController) {
      activeController.abort();
      activeController = null;
    }
    set({ query: '', results: [], facets: {}, totalResults: 0, isLoading: false, error: null });
  },

  cancelSearch: () => {
    if (activeController) {
      activeController.abort();
      activeController = null;
    }
    set({ isLoading: false });
  },

  executeSearch: async (query, workspaceId) => {
    if (query.length < 2) {
      set({ results: [], facets: {}, totalResults: 0, isLoading: false, error: null });
      return;
    }

    const cacheKey = `${query}:${workspaceId}:${get().scope}`;
    const cached = get().cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      set({
        results: cached.results,
        facets: cached.facets,
        totalResults: cached.total,
        isLoading: false,
        error: null,
      });
      return;
    }

    if (activeController) {
      activeController.abort();
    }
    activeController = new AbortController();
    const signal = activeController.signal;

    set({ isLoading: true, error: null });

    try {
      const data: SearchResponse = await searchEndpoints.search(
        query,
        workspaceId,
        get().scope,
        signal
      );

      const cacheMap = get().cache;
      if (cacheMap.size >= MAX_CACHE) {
        const oldest = cacheMap.keys().next().value;
        if (oldest) cacheMap.delete(oldest);
      }
      cacheMap.set(cacheKey, {
        results: data.results,
        facets: data.facets,
        total: data.total_results,
        timestamp: Date.now(),
      });

      set({
        results: data.results,
        facets: data.facets,
        totalResults: data.total_results,
        isLoading: false,
        error: null,
      });
    } catch (err: unknown) {
      if (isAbortError(err)) return;
      set({ isLoading: false, error: err instanceof Error ? err.message : 'Search failed' });
    }
  },
}));
