'use client';

import { InboxRouteGate } from '@/components/inbox/inbox-route-gate';

/**
 * The inbox stopped being a page in this change.
 *
 * It used to render a full-height layout with its own 200px rail, reached by
 * navigating here. It is a dialog now -- mounted once in the topbar, opened
 * over whatever you were doing -- so all this route does is make a pasted
 * `/{workspace}/inbox` open that dialog and then render nothing.
 */
export default function InboxPage() {
  return <InboxRouteGate />;
}
