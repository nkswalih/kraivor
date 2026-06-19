'use client';

import { Globe, Search } from 'lucide-react';
import { useCommunityStore } from '@/lib/stores/community-store';
import { Feed } from '@/components/community/feed';
import { FeedTabs } from '@/components/community/feed-tabs';
import { TrendingSidebar } from '@/components/community/trending-sidebar';
import { TopContributors } from '@/components/community/top-contributors';
import { CreateDialog } from '@/components/community/create-dialog';
import { TagChip } from '@/components/community/tag-chip';
import { usePopularTags } from '@/lib/hooks/use-community';

export default function CommunityPage() {
  const setCreateDialogOpen = useCommunityStore((s) => s.setCreateDialogOpen);
  const { data: tags } = usePopularTags(10);

  return (
    <div className="flex h-full w-full animate-fade-up">
      <div className="flex-1 overflow-y-auto p-6 max-w-[1000px] mx-auto border-r border-border bg-background">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-xl font-medium flex items-center gap-2 text-foreground">
              <Globe className="w-5 h-5 text-primary" /> Developer Community
            </h1>
            <p className="text-[13px] text-muted-foreground mt-1">
              Discover public reports, architecture patterns, and discussions.
            </p>
          </div>
          <button
            onClick={() => setCreateDialogOpen(true)}
            className="btn-shimmer text-primary-foreground text-[13px] font-medium px-4 py-2 rounded-md"
          >
            New Discussion
          </button>
        </div>

        <div className="flex items-center justify-between border-b border-border pb-4 mb-6">
          <FeedTabs />
          <div className="flex items-center gap-2">
            <button className="p-1.5 text-muted-foreground hover:text-foreground rounded bg-card border border-border">
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Active tag filter */}
        <ActiveTagFilter />

        <Feed />
      </div>

      <div className="w-[300px] bg-card p-6 hidden lg:block shrink-0 overflow-y-auto">
        <TrendingSidebar />

        <div className="mt-8">
          <h3 className="text-[12px] font-semibold tracking-wider text-muted-foreground uppercase mb-4">
            Popular Tags
          </h3>
          <div className="flex flex-wrap gap-2">
            {tags?.results.map((tag) => (
              <TagChip key={tag.id} name={tag.name} slug={tag.slug} />
            ))}
          </div>
        </div>

        <div className="mt-8">
          <TopContributors />
        </div>
      </div>

      <CreateDialog />
    </div>
  );
}

function ActiveTagFilter() {
  const activeTag = useCommunityStore((s) => s.activeTag);
  const setActiveTag = useCommunityStore((s) => s.setActiveTag);

  if (!activeTag) return null;

  return (
    <div className="flex items-center gap-2 mb-4 text-[12px] text-muted-foreground">
      <span>Filtering by:</span>
      <span className="text-primary font-medium">#{activeTag}</span>
      <button
        onClick={() => setActiveTag(null)}
        className="text-muted-foreground hover:text-foreground underline"
      >
        clear
      </button>
    </div>
  );
}