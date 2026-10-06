import Link from 'next/link';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Avatar } from '@/components/profiles/avatar';

/**
 * One row for "a person, as a link".
 *
 * Six places hand-rolled this and each got it slightly differently:
 * `explore-content.tsx` (a `<button>` calling `router.push`), `top-contributors.tsx`
 * (a `<Link>`), and four byte-identical blocks -- followers and following, once
 * per profile page, in two different navigators.
 *
 * The consolidation is structural. Each variant reproduces its call site's
 * classes exactly, so nothing moves or resizes by a pixel; what is shared is the
 * part that was already the same, and the place to fix truncation and overflow
 * once instead of six times.
 *
 * ## Why the row is not itself the link
 *
 * `explore-content` and `top-contributors` want a Message action on the row
 * (Task 4's acceptance requires starting a DM "from community and from search"),
 * and `<a><button></a>` is invalid HTML -- nested interactive elements are a
 * real accessibility failure, not a lint preference, and browsers resolve a
 * click on the inner button by following the outer link.
 *
 * So navigation lives on an inner `<Link>` wrapping the identity block, and
 * `actions` is a sibling of it. The trailing text stays *inside* the link,
 * because it is not interactive, which keeps the link's accessible name as
 * readable as before (a screen reader gets "Jane Doe @jane Followed 2 days ago",
 * not a bare aria-label). Clicking anywhere but the action still navigates.
 */

type Variant = 'detail' | 'search' | 'compact';

interface Style {
  row: string;
  inner: string;
  name: string;
  secondary: string;
  avatarSize: 'sm' | 'md';
}

const VARIANTS: Record<Variant, Style> = {
  /** Follower/following lists on a profile page. */
  detail: {
    row: 'flex items-center gap-3 px-3 py-2 rounded-md hover:bg-accent transition-colors',
    inner: 'flex min-w-0 flex-1 items-center gap-3',
    name: 'text-[13px] font-medium text-foreground truncate',
    secondary: 'text-[12px] text-muted-foreground truncate',
    avatarSize: 'md',
  },
  /** "People" results in search / explore. */
  search: {
    row: 'flex items-center gap-3 w-full p-2.5 rounded-lg hover:bg-muted/50 transition-colors text-left',
    inner: 'flex min-w-0 flex-1 items-center gap-3 cursor-pointer',
    name: 'text-[13px] font-medium text-foreground truncate',
    secondary: 'text-[12px] text-muted-foreground',
    avatarSize: 'sm',
  },
  /** Community sidebar. No row highlight; the name underlines. */
  compact: {
    row: 'flex items-center justify-between gap-2 group',
    inner: 'flex min-w-0 flex-1 items-center gap-2 cursor-pointer',
    name: 'text-[13px] font-medium text-foreground truncate group-hover:underline',
    secondary: 'text-[11px] text-muted-foreground',
    avatarSize: 'sm',
  },
};

export interface UserRowProps {
  href: string;
  name: string;
  /** Rendered as `@name` unless `secondary` is supplied. */
  username?: string;
  avatarUrl?: string;
  fallbackAvatarUrl?: string;
  secondary?: ReactNode;
  trailing?: ReactNode;
  /** Sibling of the link, never inside it. */
  actions?: ReactNode;
  variant?: Variant;
  className?: string;
}

export function UserRow({
  href,
  name,
  username,
  avatarUrl,
  fallbackAvatarUrl,
  secondary,
  trailing,
  actions,
  variant = 'detail',
  className,
}: UserRowProps) {
  const style = VARIANTS[variant];
  // `!== undefined`, not `??`. `secondary` is a ReactNode and `null` is a valid
  // one meaning "say nothing"; `??` would read that as absent and fall through
  // to `@username`, which is the opposite of what the caller asked for.
  const subtitle = secondary !== undefined ? secondary : username ? `@${username}` : null;

  return (
    <div className={cn(style.row, className)}>
      <Link href={href} className={style.inner}>
        <Avatar
          src={avatarUrl}
          fallbackSrc={fallbackAvatarUrl}
          name={name}
          size={style.avatarSize}
        />
        <div className="min-w-0 flex-1">
          <div className={style.name}>{name}</div>
          {subtitle !== null && (
            <div className={style.secondary}>{subtitle}</div>
          )}
        </div>
        {trailing && <div className="shrink-0">{trailing}</div>}
      </Link>
      {actions && <div className="flex shrink-0 items-center gap-1">{actions}</div>}
    </div>
  );
}