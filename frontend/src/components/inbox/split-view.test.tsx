import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SplitView } from './split-view';

/**
 * `SplitView` carries the entire responsive story for three of the five
 * sections, and it does it in CSS rather than with a `matchMedia` listener --
 * so the thing to pin is which classes land on which pane.
 *
 * jsdom does not apply stylesheets, so these assert on the classes that decide
 * the layout rather than on computed visibility. That is deliberate: the class
 * *is* the mechanism, and a test that checked `offsetWidth` would pass against
 * a component that had the right idea but the wrong classes.
 *
 * The contract in both directions:
 *  - `sm` and up, both panes are shown and the list is pinned to its width;
 *  - below `sm`, exactly one pane is shown at a time, and getting to the
 *    detail from the list goes through a Back control.
 */
function panes(container: HTMLElement) {
  const root = container.firstElementChild as HTMLElement;
  const [list, detail] = Array.from(root.children) as HTMLElement[];
  return { root, list, detail };
}

const LIST = <div data-testid="list">list content</div>;
const DETAIL = <div data-testid="detail">detail content</div>;

describe('SplitView', () => {
  it('shows both panes at rest, with the detail hidden for narrow screens only', () => {
    const { container } = render(
      <SplitView list={LIST} detail={DETAIL} hasSelection={false} onBack={() => {}} />
    );
    const { list, detail } = panes(container);

    /* The list is always present: at rest it is what a phone shows. */
    expect(list.className).not.toMatch(/(^|\s)hidden(\s|$)/);
    expect(list.className).toContain('sm:w-[320px]');

    /* The detail is the pane that moves -- hidden until something is picked
       below `sm`, and always shown above it. */
    expect(detail.className).toMatch(/(^|\s)hidden(\s|$)/);
    expect(detail.className).toContain('sm:flex');
  });

  it('swaps to the detail on a narrow screen once something is selected', () => {
    const { container } = render(
      <SplitView list={LIST} detail={DETAIL} hasSelection onBack={() => {}} />
    );
    const { list, detail } = panes(container);

    /* Below `sm` only one pane fits, so the list steps aside -- but keeps
       `sm:block` so it stays put at the breakpoint. */
    expect(list.className).toMatch(/(^|\s)hidden(\s|$)/);
    expect(list.className).toContain('sm:block');

    expect(detail.className).not.toMatch(/(^|\s)hidden(\s|$)/);
    expect(detail.className).toContain('sm:flex');
  });

  it('offers a Back control only when there is somewhere to go back to', () => {
    const { rerender, queryByRole } = render(
      <SplitView list={LIST} detail={DETAIL} hasSelection={false} onBack={() => {}} />
    );
    expect(queryByRole('button', { name: /Back/ })).not.toBeInTheDocument();

    rerender(
      <SplitView list={LIST} detail={DETAIL} hasSelection onBack={() => {}} />
    );
    expect(screen.getByRole('button', { name: /Back/ })).toBeInTheDocument();
  });

  it('hands the back request to the caller, which owns the selection', () => {
    const onBack = vi.fn();
    render(<SplitView list={LIST} detail={DETAIL} hasSelection onBack={onBack} />);

    fireEvent.click(screen.getByRole('button', { name: /Back/ }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it('keeps both panes mounted so switching back does not refetch', () => {
    const { container } = render(
      <SplitView list={LIST} detail={DETAIL} hasSelection onBack={() => {}} />
    );
    const { list, detail } = panes(container);

    /* Hidden, not removed: the list keeps its scroll position and its loaded
       rows while the detail is in front. */
    expect(list.querySelector('[data-testid="list"]')).toBeInTheDocument();
    expect(detail.querySelector('[data-testid="detail"]')).toBeInTheDocument();
  });
});
