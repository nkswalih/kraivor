'use client';

import { useCallback, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/shadcn';
import { useSettingsDialogStore } from '@/lib/stores/settings-dialog-store';
import {
  findSettingsSection,
  prefetchSettingsSections,
} from './settings-sections';
import { SectionErrorBoundary } from '@/components/ui/section-error-boundary';
import { SettingsSidebar } from './settings-sidebar';

function isSettingsPath(pathname: string, workspaceSlug: string) {
  const base = `/${workspaceSlug}/settings`;
  return pathname === base || pathname.startsWith(`${base}/`);
}

/**
 * The settings panel: a Discord-style modal with a nav rail and a body that
 * scrolls inside itself.
 *
 * It is mounted once, next to the command palette, so it can open over any
 * page in the workspace without that page going anywhere. Everything that
 * used to be a navigation is now a store write -- opening it from the sidebar
 * or ⌘K, switching sections, closing it -- which is what makes it possible to
 * open instantly, keep the app behind it, and put the user back exactly where
 * they were on Esc.
 *
 * Two lifetimes are deliberate:
 *
 *  - a route change closes it, so a link inside a section (Billing's pricing
 *    link, say) does not leave the panel floating over the page it lands on.
 *    Paths that *are* the settings routes are exempt: that is a pasted URL
 *    opening the panel, and its route gate owns that state;
 *  - each section is a lazily imported view behind a shimmer, and the panel
 *    warms every section chunk while it is up, so the first switch is a cache
 *    hit rather than a download.
 */
export function SettingsDialog({ workspaceSlug }: { workspaceSlug: string }) {
  const section = useSettingsDialogStore(s => s.section);
  const close = useSettingsDialogStore(s => s.close);
  const setSection = useSettingsDialogStore(s => s.setSection);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (isSettingsPath(pathname, workspaceSlug)) return;
    close();
  }, [pathname, close, workspaceSlug]);

  /* Deferred past the open animation, and repeated per section change only
     because it is cheap after the first call -- the guard is inside. */
  useEffect(() => {
    if (section === null) return;
    const timer = window.setTimeout(prefetchSettingsSections, 250);
    return () => window.clearTimeout(timer);
  }, [section]);

  const dismiss = useCallback(() => {
    close();
    /* A pasted URL puts the settings route itself behind the panel, and that
       route renders nothing -- leave it and closing would strand an empty
       page, so hand the address bar back to the workspace. */
    if (isSettingsPath(pathname, workspaceSlug)) {
      router.replace(`/${workspaceSlug}`);
    }
  }, [close, pathname, router, workspaceSlug]);

  const active = section === null ? null : findSettingsSection(section);

  return (
    <Dialog
      open={section !== null}
      onOpenChange={next => {
        if (!next) dismiss();
      }}
    >
      <DialogContent className="max-w-none w-[min(1040px,calc(100vw-2.5rem))] h-[min(84vh,780px)] p-0 overflow-hidden">
        <DialogTitle className="sr-only">Settings</DialogTitle>
        <DialogDescription className="sr-only">
          Manage your account and workspace settings.
        </DialogDescription>

        <div className="flex h-full min-h-0">
          <SettingsSidebar
            workspaceSlug={workspaceSlug}
            active={section ?? 'preferences'}
            onSelect={setSection}
          />

          <div className="flex-1 min-w-0 overflow-y-auto overscroll-contain">
            <div className="max-w-[820px] mx-auto px-8 py-8">
              {active ? (
                /* A view that throws on an unexpected payload must cost the
                   body, not the workspace chrome behind the panel. */
                <SectionErrorBoundary section={active.label}>
                  <active.View />
                </SectionErrorBoundary>
              ) : (
                <p className="text-sm text-text-secondary">
                  That settings section could not be found.
                </p>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
