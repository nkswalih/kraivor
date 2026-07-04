import { create } from 'zustand';

interface BreadcrumbState {
  detailTitle: string;
  setDetailTitle: (title: string) => void;
}

export const useBreadcrumbStore = create<BreadcrumbState>((set) => ({
  detailTitle: '',
  setDetailTitle: (title) => set({ detailTitle: title }),
}));
