'use client';

import { Search, List, LayoutGrid, ArrowUpDown, Filter } from 'lucide-react';
import { useCommunityStore, defaultSort } from '@/lib/stores/community-store';
import { useState } from 'react';
import type { SortOption } from '@/types/domain/community';

const SORT_OPTIONS: { label: string; value: SortOption }[] = [
  { label: 'Latest', value: 'latest' },
  { label: 'Top', value: 'top' },
];

export function FeedToolbar() {
  const activeTab = useCommunityStore(s => s.activeTab);
  const sortOption = useCommunityStore(s => s.sortOption);
  const setSortOption = useCommunityStore(s => s.setSortOption);
  const searchQuery = useCommunityStore(s => s.searchQuery);
  const setSearchQuery = useCommunityStore(s => s.setSearchQuery);
  const viewMode = useCommunityStore(s => s.viewMode);
  const setViewMode = useCommunityStore(s => s.setViewMode);
  const activeTag = useCommunityStore(s => s.activeTag);
  const setActiveTag = useCommunityStore(s => s.setActiveTag);

  const [sortOpen, setSortOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);

  const currentSort = sortOption ?? defaultSort(activeTab);
  const currentSortLabel = SORT_OPTIONS.find(o => o.value === currentSort)?.label ?? 'Latest';

  const showSort = activeTab === 'home' || activeTab === 'news';

  return (
    <div className="flex items-center justify-between gap-3 mb-4">
      {activeTab === 'explore' ? (
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search discussions..."
            className="w-full h-9 pl-9 pr-3 text-[13px] bg-card border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-primary text-foreground placeholder:text-muted-foreground"
          />
        </div>
      ) : (
        <div className="flex items-center gap-2">
          {showSort && (
            <div className="relative">
              <button
                onClick={() => setSortOpen(!sortOpen)}
                className="flex items-center gap-1.5 h-9 px-3 text-[12px] font-medium text-muted-foreground hover:text-foreground bg-card border border-border rounded-md transition-colors"
              >
                <ArrowUpDown className="w-3.5 h-3.5" />
                {currentSortLabel}
              </button>
              {sortOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setSortOpen(false)} />
                  <div className="absolute top-full left-0 mt-1 z-20 w-36 bg-card border border-border rounded-md shadow-lg py-1">
                    {SORT_OPTIONS.map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => { setSortOption(opt.value); setSortOpen(false); }}
                        className={`w-full text-left px-3 py-1.5 text-[12px] transition-colors ${
                          currentSort === opt.value
                            ? 'text-primary bg-primary/5'
                            : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
          <div className="relative">
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className={`flex items-center gap-1.5 h-9 px-3 text-[12px] font-medium bg-card border border-border rounded-md transition-colors ${
                activeTag ? 'text-primary border-primary/40' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              {activeTag ? `#${activeTag}` : 'Filter'}
            </button>
            {filterOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setFilterOpen(false)} />
                <div className="absolute top-full left-0 mt-1 z-20 w-44 bg-card border border-border rounded-md shadow-lg py-1">
                  {activeTag && (
                    <button
                      onClick={() => { setActiveTag(null); setFilterOpen(false); }}
                      className="w-full text-left px-3 py-1.5 text-[12px] text-destructive hover:bg-muted transition-colors"
                    >
                      Clear filter
                    </button>
                  )}
                  <div className="px-3 py-1.5 text-[11px] text-muted-foreground">
                    Click tags in the sidebar to filter
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <div className="flex items-center gap-1 bg-card border border-border rounded-md p-0.5">
        <button
          onClick={() => setViewMode('list')}
          className={`p-1.5 rounded transition-colors ${
            viewMode === 'list'
              ? 'text-foreground bg-muted'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <List className="w-4 h-4" />
        </button>
        <button
          onClick={() => setViewMode('grid')}
          className={`p-1.5 rounded transition-colors ${
            viewMode === 'grid'
              ? 'text-foreground bg-muted'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <LayoutGrid className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
