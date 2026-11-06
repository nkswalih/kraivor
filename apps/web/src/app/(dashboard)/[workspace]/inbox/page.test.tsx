import { describe, it, expect, beforeEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import InboxPage from './page';
import { useInboxDialogStore } from '@/lib/stores/inbox-dialog-store';

/**
 * `/{workspace}/inbox` is still a route, because a URL somebody pasted should
 * keep working -- but it is an address now, not the place the inbox lives.
 *
 * The panel is mounted once in the topbar, so this route's whole job is to
 * open it and get out of the way. What it must *not* do is render anything: a
 * non-empty body here would sit underneath the dialog, and closing the dialog
 * would strand the user on a page with nothing on it.
 *
 * The tests that used to live here -- the slug/UUID href pins -- moved with
 * the panels they covered, to
 * `src/components/inbox/inbox-sections.test.tsx`.
 */
describe('InboxRouteGate', () => {
  beforeEach(() => {
    cleanup();
    useInboxDialogStore.getState().close();
  });

  it('opens the panel on All and renders nothing itself', () => {
    const { container } = render(<InboxPage />);

    expect(useInboxDialogStore.getState().section).toBe('all');
    expect(container).toBeEmptyDOMElement();
  });

  it('leaves the panel closed until something asks for it', () => {
    expect(useInboxDialogStore.getState().section).toBeNull();
    useInboxDialogStore.getState().open('channels');
    expect(useInboxDialogStore.getState().section).toBe('channels');
    useInboxDialogStore.getState().close();
    expect(useInboxDialogStore.getState().section).toBeNull();
  });
});
