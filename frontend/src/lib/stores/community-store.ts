import { create } from 'zustand';
import type { SortOption } from '@/types/domain/community';

interface CommunityState {
  activeSort: SortOption;
  activeTag: string | null;
  searchQuery: string;
  createDialogOpen: boolean;
  setActiveSort: (sort: SortOption) => void;
  setActiveTag: (tag: string | null) => void;
  setSearchQuery: (query: string) => void;
  setCreateDialogOpen: (open: boolean) => void;
}

export const useCommunityStore = create<CommunityState>((set) => ({
  activeSort: 'trending' as SortOption,
  activeTag: null,
  searchQuery: '',
  createDialogOpen: false,
  setActiveSort: (sort) => set({ activeSort: sort }),
  setActiveTag: (tag) => set({ activeTag: tag }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setCreateDialogOpen: (open) => set({ createDialogOpen: open }),
}));
