'use client';

import { useCommunityStore } from '@/lib/stores/community-store';
import type { ActiveTab } from '@/types/domain/community';

const TABS: { label: string; value: ActiveTab }[] = [
  { label: 'Home', value: 'home' },
  { label: 'Trending', value: 'trending' },
  { label: 'Explore', value: 'explore' },
  { label: 'News', value: 'news' },
];

export function FeedTabs() {
  const activeTab = useCommunityStore(s => s.activeTab);
  const setActiveTab = useCommunityStore(s => s.setActiveTab);

  return (
    <div className="flex items-center gap-4 text-[13px] font-medium">
      {TABS.map(tab => (
        <button
          key={tab.value}
          onClick={() => setActiveTab(tab.value)}
          className={
            activeTab === tab.value
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
