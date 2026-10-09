'use client';

import Link from 'next/link';
import type { ComponentPropsWithoutRef, MouseEvent, ReactNode } from 'react';
import { useProfileDialogStore } from '@/lib/stores/profile-dialog-store';

/** The real route a profile lives on. */
export function profileHref(username: string, workspaceSlug?: string) {
  return workspaceSlug ? `/${workspaceSlug}/profile/${username}` : `/profile/${username}`;
}

type LinkProps = Omit<ComponentPropsWithoutRef<typeof Link>, 'href'>;

interface ProfileLinkProps extends LinkProps {
  username: string;
  /** Omitted on the public marketing profile, which has no dialog to open. */
  workspaceSlug?: string;
  children: ReactNode;
  /** Runs first; call `e.preventDefault()` to opt out of opening the card. */
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void;
}

/**
 * A profile link that opens the card instead of navigating.
 *
 * The `href` is kept exactly as it was, so copy-link, open-in-new-tab, and the
 * accessible name are unchanged. Only a plain left click is intercepted; every
 * modified click is handed back to the browser, because ctrl/cmd/shift-click
 * still means "new tab" to a user and nothing here is worth taking that away.
 */
export function ProfileLink({
  username,
  workspaceSlug,
  onClick,
  ...rest
}: ProfileLinkProps) {
  const open = useProfileDialogStore(s => s.open);

  return (
    <Link
      href={profileHref(username, workspaceSlug)}
      onClick={e => {
        onClick?.(e);
        if (e.defaultPrevented) return;
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
        e.preventDefault();
        open(username);
      }}
      {...rest}
    />
  );
}
