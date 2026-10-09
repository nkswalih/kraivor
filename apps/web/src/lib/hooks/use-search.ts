import { useEffect, useRef, useCallback } from 'react';
import { useSearchStore } from '@/lib/stores/search-store';

export function useSearch(workspaceId: string | null, debounceMs = 250) {
  const query = useSearchStore(s => s.query);
  const results = useSearchStore(s => s.results);
  const facets = useSearchStore(s => s.facets);
  const totalResults = useSearchStore(s => s.totalResults);
  const isLoading = useSearchStore(s => s.isLoading);
  const error = useSearchStore(s => s.error);
  const scope = useSearchStore(s => s.scope);
  const setQuery = useSearchStore(s => s.setQuery);
  const setScope = useSearchStore(s => s.setScope);
  const executeSearch = useSearchStore(s => s.executeSearch);
  const clearSearch = useSearchStore(s => s.clearSearch);
  const cancelSearch = useSearchStore(s => s.cancelSearch);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!workspaceId) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      executeSearch(query, workspaceId);
    }, debounceMs);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, workspaceId, scope, debounceMs, executeSearch]);

  const cancel = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    cancelSearch();
  }, [cancelSearch]);

  return {
    query,
    setQuery,
    setScope,
    scope,
    results,
    facets,
    totalResults,
    isLoading,
    error,
    clearSearch,
    cancel,
  };
}
