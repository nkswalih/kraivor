import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { MouseEvent } from 'react';
import { ProfileLink, profileHref } from './profile-link';
import { useProfileDialogStore } from '@/lib/stores/profile-dialog-store';

/**
 * The card replaced the profile *route* as the way you visit somebody, but the
 * route has to survive -- pasted URLs, open-in-new-tab, and the tests in this
 * repo that pin `href` -- so what these guard is the split: the href is real
 * and untouched, and only a plain left click is rerouted into the store.
 */
describe('ProfileLink', () => {
  beforeEach(() => {
    useProfileDialogStore.getState().close();
  });

  it('builds the workspace and public routes the same way the pages do', () => {
    expect(profileHref('jane', 'acme')).toBe('/acme/profile/jane');
    expect(profileHref('jane')).toBe('/profile/jane');
  });

  it('keeps the real href behind the card', () => {
    render(
      <ProfileLink username="jane" workspaceSlug="acme">
        Jane Doe
      </ProfileLink>
    );

    const link = screen.getByRole('link', { name: 'Jane Doe' });
    expect(link).toHaveAttribute('href', '/acme/profile/jane');
  });

  it('opens the card instead of navigating on a plain click', () => {
    render(
      <ProfileLink username="jane" workspaceSlug="acme">
        Jane Doe
      </ProfileLink>
    );

    fireEvent.click(screen.getByRole('link', { name: 'Jane Doe' }));
    expect(useProfileDialogStore.getState().username).toBe('jane');
  });

  it('leaves ctrl-click to the browser', () => {
    // "Open in a new tab" is not a thing to take away from someone to save a
    // navigation; the card is a convenience, not a trap.
    render(
      <ProfileLink username="jane" workspaceSlug="acme">
        Jane Doe
      </ProfileLink>
    );

    fireEvent.click(screen.getByRole('link', { name: 'Jane Doe' }), { ctrlKey: true });
    expect(useProfileDialogStore.getState().username).toBeNull();
  });

  it('lets a caller opt out by preventing the default', () => {
    const onClick = vi.fn((e: MouseEvent<HTMLAnchorElement>) => e.preventDefault());
    render(
      <ProfileLink username="jane" workspaceSlug="acme" onClick={onClick}>
        Jane Doe
      </ProfileLink>
    );

    fireEvent.click(screen.getByRole('link', { name: 'Jane Doe' }));
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(useProfileDialogStore.getState().username).toBeNull();
  });
});
