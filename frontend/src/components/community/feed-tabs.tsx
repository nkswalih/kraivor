'use client';

import { useCommunityStore } from '@/lib/stores/community-store';
import type { SortOption } from '@/types/domain/community';

const TABS: { label: string; value: SortOption }[] = [
  { label: 'Trending', value: 'trending' },
  { label: 'Latest', value: 'latest' },
  { label: 'Top', value: 'top' },
];

export function FeedTabs() {
  const activeSort = useCommunityStore((s) => s.activeSort);
  const setActiveSort = useCommunityStore((s) => s.setActiveSort);

  return (
    <div className="flex items-center gap-4 text-[13px] font-medium">
      {TABS.map((tab) => (
        <button
          key={tab.value}
          onClick={() => setActiveSort(tab.value)}
          className={
            activeSort === tab.value
              ? 'text-foreground border-b-2 border-primary pb-4 -mb-[17px]'
              : 'text-muted-foreground hover:text-foreground transition-colors'
          }
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
