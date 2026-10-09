'use client';

import { useCallback, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/shadcn';
import { SectionErrorBoundary } from '@/components/ui/section-error-boundary';
import { useInboxDialogStore } from '@/lib/stores/inbox-dialog-store';
import { findInboxSection, prefetchInboxSections } from './inbox-sections';
import { InboxSidebar } from './inbox-sidebar';

function isInboxPath(pathname: string, workspaceSlug: string) {
  const base = `/${workspaceSlug}/inbox`;
  return pathname === base || pathname.startsWith(`${base}/`);
}

/**
 * The inbox panel: a Discord-style modal with a nav rail and a body that
 * scrolls inside itself.
 *
 * It is mounted once, next to the settings panel, so it can open over any page
 * in the workspace without that page going anywhere. Everything that used to
 * be a navigation is now a store write -- opening it from the sidebar or ⌘K,
 * switching tabs, closing it -- which is what makes it possible to open
 * instantly, keep the app behind it, and put the user back exactly where they
 * were on Esc.
 *
 * Three things are deliberate:
 *
 *  - a route change closes it, so a link inside a section (a DM row in
 *    Members, "Open channel" in Channels) does not leave the panel floating
 *    over the page it lands on. Paths that *are* the inbox route are exempt:
 *    that is a pasted URL opening the panel, and its route gate owns that
 *    state;
 *  - each tab is a lazily imported view behind a shimmer, and the panel warms
 *    every section chunk shortly after it opens, so the first switch is a
 *    cache hit rather than a download;
 *  - it is a full-screen sheet below `sm` and a centred dialog above it. On a
 *    phone there is no width to spare for a rail plus two panes, so the rail
 *    unrolls into a strip and `SplitView` shows one pane at a time -- all of it
 *    class swapping, with no JS measuring the viewport.
 */
export function InboxDialog({ workspaceSlug }: { workspaceSlug: string }) {
  const section = useInboxDialogStore(s => s.section);
  const close = useInboxDialogStore(s => s.close);
  const setSection = useInboxDialogStore(s => s.setSection);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (isInboxPath(pathname, workspaceSlug)) return;
    close();
  }, [pathname, close, workspaceSlug]);

  /* Deferred past the open animation so the section somebody asked for wins
     the race, and repeated per tab change only because it is cheap after the
     first call -- the guard is inside. */
  useEffect(() => {
    if (section === null) return;
    const timer = window.setTimeout(prefetchInboxSections, 250);
    return () => window.clearTimeout(timer);
  }, [section]);

  const dismiss = useCallback(() => {
    close();
    /* A pasted URL puts the inbox route itself behind the panel, and that route
       renders nothing -- leave it and closing would strand an empty page, so
       hand the address bar back to the workspace. */
    if (isInboxPath(pathname, workspaceSlug)) {
      router.replace(`/${workspaceSlug}`);
    }
  }, [close, pathname, router, workspaceSlug]);

  const active = section === null ? null : findInboxSection(section);

  return (
    <Dialog
      open={section !== null}
      onOpenChange={next => {
        if (!next) dismiss();
      }}
    >
      <DialogContent
        className="
          max-w-none p-0 overflow-hidden
          w-full h-[100dvh] rounded-none
          sm:rounded-xl sm:h-[min(86vh,800px)] sm:w-[min(1040px,calc(100vw-2.5rem))]
        "
      >
        <DialogTitle className="sr-only">Inbox</DialogTitle>
        <DialogDescription className="sr-only">
          Notifications, invitations, and activity across your workspaces.
        </DialogDescription>

        <div className="flex h-full min-h-0 flex-col bg-[#0A0A0B]">
          {/* A real row rather than content with a corner kept clear.
              `DialogContent` draws its close button at `right-4 top-4`, which
              would otherwise sit over the detail pane's first line -- a long
              notification title runs straight under it. Pinning a 49px header
              across the full width puts the button in a row that holds nothing
              but the title, at every breakpoint. */}
          <div className="h-[49px] shrink-0 flex items-center border-b border-[#27272A] bg-[#111113] px-4 pr-12">
            <span className="text-[13px] font-semibold text-[#FAFAFA]">Inbox</span>
          </div>

          <div className="flex flex-col sm:flex-row flex-1 min-h-0">
            <InboxSidebar active={section ?? 'all'} onSelect={setSection} />

            <div className="flex-1 min-h-0 min-w-0 flex flex-col overflow-hidden">
              {active && (
                /* A view that throws on an unexpected payload must cost the
                   body, not the workspace chrome behind the panel. */
                <SectionErrorBoundary
                  section={active.label}
                  className="flex-1 min-h-0 flex flex-col overflow-hidden"
                >
                  <active.View />
                </SectionErrorBoundary>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
