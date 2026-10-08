'use client';

import { useParams } from 'next/navigation';
import { useTopContributors } from '@/lib/hooks/use-profiles';
import { UserRow } from '@/components/users/user-row';
import { Skeleton } from '@/components/ui/shadcn';

// No MessageButton here on purpose: direct messages start from the member's
// own profile, so the list stays a list -- rank, name, discussion count --
// instead of offering a second way to DM somebody from a ranking widget.

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
            <UserRow
              key={user.user_id}
              variant="compact"
              href={`/${workspace}/profile/${user.username}`}
              name={user.display_name}
              avatarUrl={user.avatar_url}
              fallbackAvatarUrl={user.user_avatar_url}
              secondary={`${user.discussion_count} discussions`}
              trailing={
                <span className="text-[11px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                  {user.reputation_score >= 1000
                    ? `${(user.reputation_score / 1000).toFixed(1)}k`
                    : user.reputation_score}
                </span>
              }
            />
          ))}
        </div>
      )}
    </>
  );
}
