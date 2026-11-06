'use client';

import dynamic from 'next/dynamic';
import type { ComponentType } from 'react';
import {
  Bot,
  Building2,
  CreditCard,
  KeyRound,
  Sliders,
  User,
  Users,
  Bell,
  type LucideIcon,
} from 'lucide-react';
import type { SettingsSection } from '@/lib/stores/settings-dialog-store';
import { SectionSkeleton } from './settings-skeletons';

export type SettingsGroup = 'Personal' | 'Administration';

export interface SettingsSectionDef {
  id: SettingsSection;
  label: string;
  icon: LucideIcon;
  group: SettingsGroup;
  /** The section body. Shimmers until its chunk lands. */
  View: ComponentType;
  /** The same import `View` wraps, kept reachable so it can be warmed. */
  load: () => Promise<ComponentType>;
}

function defineSection(
  id: SettingsSection,
  group: SettingsGroup,
  label: string,
  icon: LucideIcon,
  load: () => Promise<ComponentType>
): SettingsSectionDef {
  return {
    id,
    group,
    label,
    icon,
    load,
    View: dynamic(() => load().then(View => ({ default: View })), {
      ssr: false,
      loading: SectionSkeleton,
    }),
  };
}

/**
 * The one list that says what settings contains.
 *
 * It replaces the `navCategories` array that used to live in the sidebar (which
 * only the sidebar could read) and the eight route files that each imported one
 * view statically -- a split that meant the nav could drift from what actually
 * rendered, and that shipped every section's code on every settings visit.
 *
 * Each view is now behind its own chunk. `load` is exported alongside `View`
 * for one reason: the dialog calls every loader on idle after it opens, so by
 * the time somebody clicks a second section there is nothing left to download.
 */
export const SETTINGS_SECTIONS: SettingsSectionDef[] = [
  defineSection('preferences', 'Personal', 'Preferences', Sliders, () =>
    import('./preferences-view').then(m => m.PreferencesView)
  ),
  defineSection('profile', 'Personal', 'Profile', User, () =>
    import('./profile-view').then(m => m.ProfileView)
  ),
  defineSection('inbox', 'Personal', 'Inbox', Bell, () =>
    import('./inbox-view').then(m => m.InboxView)
  ),
  defineSection('security', 'Personal', 'Security & Keys', KeyRound, () =>
    import('./security-and-keys-view').then(m => m.SecurityAndKeysView)
  ),
  defineSection('ai-providers', 'Personal', 'AI Providers', Bot, () =>
    import('./ai-providers-view').then(m => m.AiProvidersView)
  ),
  defineSection('billing', 'Administration', 'Billing', CreditCard, () =>
    import('./billing-view').then(m => m.BillingView)
  ),
  defineSection('workspace', 'Administration', 'Workspace', Building2, () =>
    import('./workspace-view').then(m => m.WorkspaceView)
  ),
  defineSection('members', 'Administration', 'Members', Users, () =>
    import('./members-view').then(m => m.MembersView)
  ),
];

export const SETTINGS_GROUPS: SettingsGroup[] = ['Personal', 'Administration'];

export function findSettingsSection(id: SettingsSection): SettingsSectionDef {
  return (
    SETTINGS_SECTIONS.find(s => s.id === id) ?? SETTINGS_SECTIONS[0]
  );
}

let warmed = false;

/**
 * Pull every section chunk into the bundler cache. Deferred to idle after the
 * panel opens, so the section somebody actually asked for wins the race, and
 * guarded so repeated opens do nothing. Failures are swallowed on purpose --
 * a section that fails to warm still loads on demand, behind the same shimmer.
 */
export function prefetchSettingsSections(): void {
  if (warmed) return;
  warmed = true;
  for (const section of SETTINGS_SECTIONS) {
    section.load().catch(() => {
      /* Leave `warmed` alone: the chunk is either cached or it is not, and a
         retry would only re-issue the same import. */
    });
  }
}
