'use client';

import { useState } from 'react';
import { Search, Loader2, ExternalLink } from 'lucide-react';
import { useKnowledgeSearch } from '@/lib/hooks/use-knowledge-dashboard';

export function KnowledgeSearchPanel({ workspaceId }: { workspaceId: string }) {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const search = useKnowledgeSearch(workspaceId, debouncedQuery);

  const handleSearch = () => {
    setDebouncedQuery(query);
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Search bar */}
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search your knowledge base..."
            className="w-full pl-9 pr-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={!query.trim() || search.isLoading}
          className="px-4 py-2 bg-venom-yellow text-black text-[12px] font-medium rounded-lg hover:brightness-110 transition-all disabled:opacity-50 flex items-center gap-1.5"
        >
          {search.isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Search className="w-3.5 h-3.5" />
          )}
          Search
        </button>
      </div>

      {/* Results */}
      {search.data && (
        <div>
          <div className="text-[12px] text-muted-foreground mb-3">
            {search.data.total} result{search.data.total !== 1 ? 's' : ''} found
          </div>
          <div className="space-y-2">
            {search.data.results.map((result, i) => (
              <div
                key={i}
                className="bg-card border border-border rounded-lg p-4 hover:border-venom-yellow/30 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h4 className="text-[13px] font-medium text-foreground truncate">
                      {result.title || 'Untitled'}
                    </h4>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      {result.source}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11px] text-venom-yellow font-medium">
                      {Math.round(result.similarity * 100)}% match
                    </span>
                    <a
                      href={result.source}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
                <p className="text-[12px] text-muted-foreground mt-2 line-clamp-3">
                  {result.content}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!search.data && !search.isLoading && debouncedQuery && (
        <div className="text-center py-12">
          <Search className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-[13px] text-muted-foreground">No results found</p>
        </div>
      )}

      {!debouncedQuery && (
        <div className="text-center py-12">
          <Search className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-[13px] text-muted-foreground">
            Search across all your knowledge items
          </p>
          <p className="text-[11px] text-muted-foreground mt-1">
            Supports semantic search, full-text search, and filtered queries
          </p>
        </div>
      )}
    </div>
  );
}
