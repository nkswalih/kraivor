'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useTopContributors } from '@/lib/hooks/use-profiles';
import { Avatar } from '@/components/profiles/avatar';
import { Skeleton } from '@/components/ui/shadcn';

export function TopContributors() {
  const params = useParams();
  const workspace = params?.workspace as string;
  const { data, isLoading } = useTopContributors(5);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Skeleton variant="circle" className="w-7 h-7" />
              <div className="space-y-1">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-2.5 w-14" />
              </div>
            </div>
            <Skeleton className="h-5 w-10 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      <h3 className="text-[12px] font-semibold tracking-wider text-muted-foreground uppercase mb-4">
        Top Contributors
      </h3>
      {!data?.results?.length ? (
        <p className="text-[12px] text-muted-foreground">No contributors yet</p>
      ) : (
        <div className="space-y-3">
          {data.results.map(user => (
            <Link
              key={user.user_id}
              href={`/${workspace}/profile/${user.username}`}
              className="flex items-center justify-between group cursor-pointer"
            >
              <div className="flex items-center gap-2 min-w-0">
                <Avatar
                  src={user.avatar_url}
                  fallbackSrc={user.user_avatar_url}
                  name={user.display_name}
                  size="sm"
                />
                <div className="min-w-0">
                  <div className="text-[13px] font-medium text-foreground group-hover:underline truncate">
                    {user.display_name}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {user.discussion_count} discussions
                  </div>
                </div>
              </div>
              <span className="text-[11px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded shrink-0">
                {user.reputation_score >= 1000
                  ? `${(user.reputation_score / 1000).toFixed(1)}k`
                  : user.reputation_score}
              </span>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
