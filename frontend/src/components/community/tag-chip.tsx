'use client';

import { useCommunityStore } from '@/lib/stores/community-store';

interface TagChipProps {
  name: string;
  slug?: string;
  size?: 'sm' | 'md';
}

export function TagChip({ name, slug, size = 'sm' }: TagChipProps) {
  const setActiveTag = useCommunityStore((s) => s.setActiveTag);
  const activeTag = useCommunityStore((s) => s.activeTag);
  const isActive = activeTag === (slug ?? name.toLowerCase());

  return (
    <button
      onClick={() => setActiveTag(isActive ? null : (slug ?? name.toLowerCase()))}
      className={`
        inline-flex items-center rounded-full border transition-colors
        ${size === 'sm' ? 'px-2.5 py-0.5 text-[11px]' : 'px-3 py-1 text-[12px]'}
        ${isActive
          ? 'bg-primary/10 border-primary/30 text-primary'
          : 'bg-background border-border text-muted-foreground hover:text-foreground hover:border-primary/50'
        }
      `}
    >
      #{name}
    </button>
  );
}
