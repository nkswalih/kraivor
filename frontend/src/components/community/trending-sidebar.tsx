'use client';

import { useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTrending } from '@/lib/hooks/use-community';
import { useAuthorProfiles } from '@/lib/hooks/use-profiles';
import { Avatar } from '@/components/profiles/avatar';
import { TrendingUp, MessageSquare } from 'lucide-react';
import { Skeleton } from '@/components/ui/shadcn';

export function TrendingSidebar() {
  const router = useRouter();
  const params = useParams();
  const workspace = params?.workspace as string;
  const { data, isLoading } = useTrending(5);

  const authorIds = useMemo(
    () => [...new Set((data?.results ?? []).map(d => d.author_id).filter(Boolean))],
    [data?.results]
  );
  const { data: resolvedData } = useAuthorProfiles(authorIds);
  const profileMap = resolvedData?.profileMap ?? {};

  return (
    <>
      <h3 className="text-[12px] font-semibold tracking-wider text-muted-foreground uppercase mb-4">
        Trending Discussions
      </h3>
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-start gap-2">
              <Skeleton variant="rect" className="w-4 h-4 shrink-0" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {data?.results.map(d => {
            const author = d.author_id ? profileMap?.[d.author_id] : undefined;
            const displayName = author?.display_name ?? d.author_display_name;
            const avatarUrl = author?.avatar_url ?? d.author_avatar_url;
            return (
              <div
                key={d.id}
                onClick={() => router.push(`/${workspace}/community/${d.id}`)}
                className="group cursor-pointer"
              >
                <div className="flex items-start gap-2">
                  <TrendingUp className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium text-foreground group-hover:text-primary transition-colors truncate">
                      {d.title}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-muted-foreground mt-0.5">
                      <span className="flex items-center gap-1.5">
                        <Avatar src={avatarUrl} name={displayName} size="sm" />
                        {displayName}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" /> {d.comment_count}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
