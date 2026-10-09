'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/lib/stores/auth-store';
import type { SettingsSection } from '@/lib/stores/settings-dialog-store';
import { SETTINGS_GROUPS, SETTINGS_SECTIONS } from './settings-sections';

interface SettingsSidebarProps {
  workspaceSlug: string;
  active: SettingsSection;
  onSelect: (section: SettingsSection) => void;
}

/**
 * The left column of the settings panel.
 *
 * It used to be a page sidebar: it read the active item off the pathname, drew
 * a "Back to app" link, and navigated on every click. As a panel it does none
 * of that -- the dialog it lives in has its own close control, and switching
 * sections writes the store instead of changing the URL, which is why the app
 * underneath never goes anywhere.
 *
 * The items still carry real `href`s, so the rail is a normal link list to the
 * keyboard and to right-click; only a plain left click is rerouted into the
 * dialog, the same split `ProfileLink` uses.
 */
export function SettingsSidebar({ workspaceSlug, active, onSelect }: SettingsSidebarProps) {
  const [query, setQuery] = useState('');
  const user = useAuthStore(s => s.user);

  const groups = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return SETTINGS_GROUPS.map(group => ({
      group,
      items: SETTINGS_SECTIONS.filter(
        s => s.group === group && (!needle || s.label.toLowerCase().includes(needle))
      ),
    })).filter(g => g.items.length > 0);
  }, [query]);

  const displayName = user?.name || user?.email?.split('@')[0] || 'Your account';

  return (
    <div className="w-[260px] shrink-0 border-r border-krait-border bg-krait-void flex flex-col min-h-0">
      {/* Who these settings belong to. Mirrors Discord's account header: one
          glance at the top of the rail, and a shortcut into the Profile
          section that is one click instead of a hunt through the list. */}
      <div className="flex items-center gap-3 px-5 pt-5 pb-4 border-b border-krait-border">
        {user?.avatar_url ? (
          <img
            src={user.avatar_url}
            alt=""
            className="w-10 h-10 rounded-full object-cover shrink-0 border border-krait-border"
          />
        ) : (
          <div className="w-10 h-10 rounded-full bg-primary/15 border border-primary/25 flex items-center justify-center text-primary text-[15px] font-semibold shrink-0">
            {displayName.charAt(0).toUpperCase()}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-text-primary truncate leading-tight">
            {displayName}
          </p>
          {user?.email && (
            <p className="text-[11px] text-text-tertiary truncate leading-tight mt-0.5">
              {user.email}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => onSelect('profile')}
          className="text-[11px] font-medium text-text-secondary hover:text-text-primary transition-colors shrink-0"
        >
          Edit profile
        </button>
      </div>

      {/* Search filters the rail, the way Discord's does. Eight sections is
          few, but it costs nothing to keep and it is where people look first. */}
      <div className="px-4 pt-4 pb-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search settings"
            aria-label="Search settings"
            className="w-full h-8 pl-8 pr-2.5 rounded-md bg-krait-obsidian border border-krait-border text-[12px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-krait-borderHi transition-colors"
          />
        </div>
      </div>

      <nav className="flex-1 min-h-0 overflow-y-auto px-2.5 pb-5 space-y-4">
        {groups.map(({ group, items }) => (
          <div key={group}>
            <p className="px-2.5 mb-1.5 text-[10px] font-semibold tracking-[0.08em] uppercase text-text-tertiary">
              {group}
            </p>
            <ul className="space-y-0.5">
              {items.map(item => {
                const Icon = item.icon;
                const isActive = item.id === active;
                return (
                  <li key={item.id}>
                    <Link
                      href={`/${workspaceSlug}/settings/${item.id}`}
                      onClick={e => {
                        e.preventDefault();
                        onSelect(item.id);
                      }}
                      aria-current={isActive ? 'page' : undefined}
                      className={cn(
                        'group flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] font-medium transition-colors relative',
                        isActive
                          ? 'bg-krait-surface2 text-text-primary'
                          : 'text-text-tertiary hover:bg-krait-surface1/60 hover:text-text-primary'
                      )}
                    >
                      {isActive && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-[2px] rounded-full bg-primary" />
                      )}
                      <Icon
                        className={cn(
                          'w-4 h-4 shrink-0 transition-colors',
                          isActive
                            ? 'text-text-primary'
                            : 'text-text-tertiary group-hover:text-text-secondary'
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}

        {groups.length === 0 && (
          <p className="px-2.5 py-2 text-[12px] text-text-tertiary">
            No settings match &ldquo;{query.trim()}&rdquo;.
          </p>
        )}
      </nav>
    </div>
  );
}
