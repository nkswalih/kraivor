'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useUI } from '@/lib/hooks';
import { Button } from '@/components/ui/shadcn';
import {
  LayoutDashboard,
  GitBranch,
  MessageSquare,
  FileText,
  Kanban,
  Settings,
  ChevronLeft,
  ChevronRight,
  Layers,
} from 'lucide-react';

const navItems = [
  { href: '/[workspace]/(dashboard)', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/[workspace]/(routes)/analysis', icon: GitBranch, label: 'Analysis' },
  { href: '/[workspace]/(routes)/ai', icon: MessageSquare, label: 'AI Chat' },
  { href: '/[workspace]/(routes)/notes', icon: FileText, label: 'Notes' },
  { href: '/[workspace]/(routes)/projects', icon: Kanban, label: 'Projects' },
];

const bottomNavItems = [{ href: '/[workspace]/settings', icon: Settings, label: 'Settings' }];

interface SidebarProps {
  workspaceSlug: string;
}

export function Sidebar({ workspaceSlug }: SidebarProps) {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebarCollapse } = useUI();

  const isActive = (href: string) => {
    const basePath = href.replace('/[workspace]/', `/${workspaceSlug}/`);
    return pathname.startsWith(basePath);
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r bg-card transition-all duration-200',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex h-full flex-col">
        <div className={cn('flex h-14 items-center border-b px-4', sidebarCollapsed ? 'justify-center' : 'justify-start gap-2')}>
          <Layers className="h-6 w-6 text-primary" />
          {!sidebarCollapsed && <span className="font-semibold">Kraivor</span>}
        </div>

        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={`/${workspaceSlug}${item.href.replace('/[workspace]/', '')}`}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  active ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  sidebarCollapsed && 'justify-center px-2'
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="border-t p-2">
          {bottomNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={`/${workspaceSlug}${item.href.replace('/[workspace]/', '')}`}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  active ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  sidebarCollapsed && 'justify-center px-2'
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
          <Button variant="ghost" size="sm" className={cn('w-full mt-2', sidebarCollapsed && 'px-2')} onClick={toggleSidebarCollapse}>
            {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            {!sidebarCollapsed && <span className="ml-2">Collapse</span>}
          </Button>
        </div>
      </div>
    </aside>
  );
}