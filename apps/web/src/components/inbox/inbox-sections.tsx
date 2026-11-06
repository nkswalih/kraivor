'use client';

import dynamic from 'next/dynamic';
import type { ComponentType } from 'react';
import { Bell, Building2, Hash, Mail, Users, type LucideIcon } from 'lucide-react';
import type { InboxSection } from '@/lib/stores/inbox-dialog-store';
import { InboxSectionSkeleton } from './inbox-skeletons';

export interface InboxSectionDef {
  id: InboxSection;
  label: string;
  icon: LucideIcon;
  /** The section body. Shimmers until its chunk lands. */
  View: ComponentType;
  /** The same import `View` wraps, kept reachable so it can be warmed. */
  load: () => Promise<ComponentType>;
}

function defineSection(
  id: InboxSection,
  label: string,
  icon: LucideIcon,
  load: () => Promise<ComponentType>
): InboxSectionDef {
  return {
    id,
    label,
    icon,
    load,
    View: dynamic(() => load().then(View => ({ default: View })), {
      ssr: false,
      loading: InboxSectionSkeleton,
    }),
  };
}

/**
 * The one list that says what the inbox contains.
 *
 * It replaces the `TABS` array that used to live in `inbox/page.tsx`, which
 * was unreachable from anywhere else -- and that page imported all five panels
 * statically, so opening the inbox shipped every one of them whether or not
 * you clicked past "All". Each section is behind its own chunk now.
 *
 * `load` is exported alongside `View` for one reason: the dialog calls every
 * loader shortly after it opens, so by the time somebody clicks a second tab
 * there is nothing left to download and the switch is a cache hit.
 */
export const INBOX_SECTIONS: InboxSectionDef[] = [
  defineSection('all', 'All', Bell, () =>
    import('./all-section').then(m => m.AllSection)
  ),
  defineSection('invitations', 'Invitations', Mail, () =>
    import('./invitations-section').then(m => m.InvitationsSection)
  ),
  defineSection('workspaces', 'Workspaces', Building2, () =>
    import('./workspaces-section').then(m => m.WorkspacesSection)
  ),
  defineSection('members', 'Members', Users, () =>
    import('./members-section').then(m => m.MembersSection)
  ),
  defineSection('channels', 'Channels', Hash, () =>
    import('./channels-section').then(m => m.ChannelsSection)
  ),
];

export function findInboxSection(id: InboxSection): InboxSectionDef {
  return INBOX_SECTIONS.find(s => s.id === id) ?? INBOX_SECTIONS[0];
}

let warmed = false;

/**
 * Pull every section chunk into the bundler cache. Deferred to shortly after
 * the panel opens, so the section somebody actually asked for wins the race,
 * and guarded so repeated opens do nothing. Failures are swallowed on purpose
 * -- a section that fails to warm still loads on demand, behind the same
 * shimmer.
 */
export function prefetchInboxSections(): void {
  if (warmed) return;
  warmed = true;
  for (const section of INBOX_SECTIONS) {
    section.load().catch(() => {
      /* Leave `warmed` alone: the chunk is either cached or it is not, and a
         retry would only re-issue the same import. */
    });
  }
}
