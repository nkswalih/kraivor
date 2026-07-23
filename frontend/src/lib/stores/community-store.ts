import { create } from 'zustand';
import type { ActiveTab, SortOption, ViewMode } from '@/types/domain/community';

interface CommunityState {
  activeTab: ActiveTab;
  sortOption: SortOption | null;
  activeTag: string | null;
  searchQuery: string;
  createDialogOpen: boolean;
  viewMode: ViewMode;
  setActiveTab: (tab: ActiveTab) => void;
  setSortOption: (sort: SortOption | null) => void;
  setActiveTag: (tag: string | null) => void;
  setSearchQuery: (query: string) => void;
  setCreateDialogOpen: (open: boolean) => void;
  setViewMode: (mode: ViewMode) => void;
}

function defaultSort(tab: ActiveTab): SortOption {
  if (tab === 'trending') return 'trending';
  if (tab === 'news') return 'top';
  return 'latest';
}

export const useCommunityStore = create<CommunityState>(set => ({
  activeTab: 'home',
  sortOption: null,
  activeTag: null,
  searchQuery: '',
  createDialogOpen: false,
  viewMode: 'list',
  setActiveTab: tab => set({ activeTab: tab, activeTag: null, searchQuery: '', sortOption: null }),
  setSortOption: sort => set({ sortOption: sort }),
  setActiveTag: tag => set({ activeTag: tag }),
  setSearchQuery: query => set({ searchQuery: query }),
  setCreateDialogOpen: open => set({ createDialogOpen: open }),
  setViewMode: mode => set({ viewMode: mode }),
}));

export { defaultSort };
