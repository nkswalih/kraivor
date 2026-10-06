import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UserRow } from './user-row';

/**
 * Six hand-rolled versions of this row were in the tree, all slightly different
 * and none tested:
 *
 *   - `explore-content.tsx` rendered it as a `<button>` calling `router.push`,
 *     so it could not be opened in a new tab and announced as a button rather
 *     than a link;
 *   - `top-contributors.tsx` used `<Link>` with a reputation badge and an 11px
 *     secondary line;
 *   - followers and following were byte-identical blocks, written twice per
 *     profile page across two navigators (one `<Link>` with a workspace segment,
 *     one bare `<a>` without).
 *
 * These pin the three things that are easy to get wrong when a row grows an
 * action slot: that navigation stays on the link rather than moving to a
 * wrapper, that the trailing text stays *inside* the link so the accessible name
 * remains readable, and that the action is never nested inside the link.
 */

function renderRow(props: Partial<Parameters<typeof UserRow>[0]> = {}) {
  return render(
    <UserRow
      href="/acme/profile/jane"
      name="Jane Doe"
      username="jane"
      {...props}
    />
  );
}

describe('UserRow', () => {
  it('links the identity block to the profile', () => {
    renderRow();

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/acme/profile/jane');
    expect(link).toHaveAccessibleName(/Jane Doe/);
  });

  it('names the person in the link, not only the avatar', () => {
    // The old followers block put both in the link too, so this is a regression
    // guard rather than a new claim -- but it is the thing that breaks first if
    // the action slot is ever moved inside the link by wrapping it.
    renderRow({ trailing: <span>Followed 2 days ago</span> });

    expect(screen.getByRole('link')).toHaveAccessibleName(
      /Jane Doe @jane Followed 2 days ago/i
    );
  });

  it('renders @username when no secondary is given', () => {
    renderRow();
    expect(screen.getByText('@jane')).toBeInTheDocument();
  });

  it('renders a supplied secondary instead', () => {
    // `explore-content` shows rep here and `top-contributors` shows a discussion
    // count -- neither of which is the handle.
    renderRow({ secondary: '12 discussions' });
    expect(screen.queryByText('@jane')).not.toBeInTheDocument();
    expect(screen.getByText('12 discussions')).toBeInTheDocument();
  });

  it('renders no secondary at all when there is nothing to say', () => {
    renderRow({ secondary: null });
    expect(screen.queryByText('@jane')).not.toBeInTheDocument();
  });

  it('keeps the action outside the link', () => {
    // The load-bearing one. `<a><button></a>` is invalid HTML, and a browser
    // resolves a click on the inner button by following the outer link -- so
    // pressing Message would navigate instead of messaging.
    renderRow({ actions: <button aria-label="Message Jane Doe" /> });

    const link = screen.getByRole('link');
    expect(link.querySelector('button')).toBeNull();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('keeps trailing text inside the link', () => {
    // Trailing is the reputation badge and the "Followed ..." line. If it were
    // hoisted outside the link the accessible name would lose it, and the badge
    // would stop being clickable along with the rest of the row.
    renderRow({ trailing: <span>42k</span> });

    const link = screen.getByRole('link');
    expect(link).toHaveTextContent('42k');
    expect(link).toHaveAccessibleName(/42k/);
  });

  it('still navigates when an action is present', () => {
    renderRow({ actions: <button aria-label="Message Jane Doe" /> });

    // Both exist, the link has an accessible name, and the action is reachable.
    expect(screen.getByRole('link', { name: /Jane Doe/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Message Jane Doe/ })).toBeInTheDocument();
  });

  it('does not render an action container when none is given', () => {
    const { container } = renderRow();

    // An empty wrapper would add an unstyled element between rows and change the
    // flex spacing of every list that has no action.
    expect(container.firstElementChild?.childElementCount).toBe(1);
  });

  it('accepts a custom class without losing the variant', () => {
    const { container } = renderRow({ className: 'mt-4' });
    expect(container.firstElementChild).toHaveClass('mt-4');
    expect(container.firstElementChild).toHaveClass('hover:bg-accent');
  });

  it('renders the detail variant by default', () => {
    // What the profile pages use, and the one with the most rows behind it.
    const { container } = renderRow();
    expect(container.firstElementChild).toHaveClass('px-3');
    expect(container.firstElementChild).toHaveClass('py-2');
    expect(container.firstElementChild).toHaveClass('rounded-md');
  });

  it('renders the search variant', () => {
    const { container } = renderRow({ variant: 'search' });
    expect(container.firstElementChild).toHaveClass('p-2.5');
    expect(container.firstElementChild).toHaveClass('rounded-lg');
    expect(container.firstElementChild).toHaveClass('hover:bg-muted/50');
  });

  it('renders the compact variant with its underline affordance', () => {
    // This variant has no row highlight, so the underline is the only hover
    // feedback. Losing it would leave the sidebar row looking inert.
    const { container } = renderRow({ variant: 'compact' });
    expect(container.firstElementChild).toHaveClass('group');
    expect(screen.getByText('Jane Doe')).toHaveClass('group-hover:underline');
  });

  it('uses the larger avatar the profile pages use, and the smaller one for the sidebar', () => {
    // `Avatar` maps `size` to a class, so assert on what it renders rather than
    // on the prop handed to it -- passing `size` down unchecked is exactly the
    // sort of thing that would otherwise go untested.
    //
    //   sm -> w-6 h-6, md -> w-10 h-10  (avatar.tsx:12-13)
    const detail = renderRow({ variant: 'detail' });
    expect(detail.container.querySelector('.w-10')).not.toBeNull();
    expect(detail.container.querySelector('.w-6')).toBeNull();
    detail.unmount();

    const search = renderRow({ variant: 'search' });
    expect(search.container.querySelector('.w-6')).not.toBeNull();
    expect(search.container.querySelector('.w-10')).toBeNull();
    search.unmount();

    const compact = renderRow({ variant: 'compact' });
    expect(compact.container.querySelector('.w-6')).not.toBeNull();
  });
});