'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import {
  User,
  Sliders,
  Bell,
  KeyRound,
  CreditCard,
  Building2,
  Users,
  ChevronRight,
  ArrowLeft,
  Bot,
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

interface NavCategory {
  label: string;
  items: NavItem[];
}

const navCategories: NavCategory[] = [
  {
    label: 'Personal',
    items: [
      { label: 'Preferences', href: 'preferences', icon: Sliders },
      { label: 'Profile', href: 'profile', icon: User },
      { label: 'Inbox', href: 'inbox', icon: Bell },
      { label: 'Security & Keys', href: 'security', icon: KeyRound },
      { label: 'AI Providers', href: 'ai-providers', icon: Bot },
    ],
  },
  {
    label: 'Administration',
    items: [
      { label: 'Billing', href: 'billing', icon: CreditCard },
      { label: 'Workspace', href: 'workspace', icon: Building2 },
      { label: 'Members', href: 'members', icon: Users },
    ],
  },
];

export function SettingsSidebar({ workspaceSlug }: { workspaceSlug: string }) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === 'preferences') {
      return pathname === `/${workspaceSlug}/settings` || pathname === `/${workspaceSlug}/settings/preferences`;
    }
    return pathname === `/${workspaceSlug}/settings/${href}`;
  };

  return (
    <nav className="w-[220px] shrink-0 border-r border-krait-border bg-krait-obsidian flex flex-col py-6 overflow-y-auto">
      <div className="px-5 mb-6">
        <Link
          href={`/${workspaceSlug}`}
          className="flex items-center gap-1.5 text-[11px] text-text-tertiary hover:text-text-secondary transition-colors mb-3"
        >
          <ArrowLeft className="w-3 h-3" />
          Back to app
        </Link>
        <h1 className="text-sm font-semibold text-text-primary tracking-tight">Settings</h1>
        <p className="text-[11px] text-text-secondary mt-0.5 tracking-wide">Manage your account</p>
      </div>

      {navCategories.map(category => (
        <div key={category.label} className="mb-5">
          <p className="px-5 mb-1.5 text-[10px] font-semibold tracking-[0.08em] uppercase text-text-tertiary">
            {category.label}
          </p>
          {category.items.map(item => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={`/${workspaceSlug}/settings/${item.href}`}
                className={cn(
                  'group flex items-center gap-2.5 px-5 py-1.5 text-[13px] font-medium transition-all duration-150 relative',
                  active
                    ? 'text-text-primary'
                    : 'text-text-tertiary hover:text-text-secondary'
                )}
              >
                <Icon className={cn(
                  'w-4 h-4 shrink-0 transition-colors duration-150',
                  active ? 'text-text-primary' : 'text-text-tertiary group-hover:text-text-secondary'
                )} />
                <span>{item.label}</span>
                {active && (
                  <ChevronRight className="w-3 h-3 ml-auto text-text-tertiary" />
                )}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
