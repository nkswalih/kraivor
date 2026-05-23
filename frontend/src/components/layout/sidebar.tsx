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

interface NavItem {
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

const getNavItems = (slug: string): NavItem[] => [
  { path: `/${slug}`, icon: LayoutDashboard, label: 'Dashboard' },
  { path: `/${slug}/analysis`, icon: GitBranch, label: 'Analysis' },
  { path: `/${slug}/ai`, icon: MessageSquare, label: 'AI Chat' },
  { path: `/${slug}/notes`, icon: FileText, label: 'Notes' },
  { path: `/${slug}/projects`, icon: Kanban, label: 'Projects' },
];

const getBottomNavItems = (slug: string): NavItem[] => [
  { path: `/${slug}/settings/security`, icon: Settings, label: 'Settings' },
];

interface SidebarProps {
  workspaceSlug: string;
}

export function Sidebar({ workspaceSlug }: SidebarProps) {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebarCollapse } = useUI();

  const isActive = (path: string) => {
    // Main dashboard route
    if (path === `/${workspaceSlug}`) {
      return pathname === path;
    }

    // Settings section
    if (path.includes('/settings')) {
      return pathname.includes('/settings');
    }

    return pathname.startsWith(path);
  };

  const navItems = getNavItems(workspaceSlug);
  const bottomNavItems = getBottomNavItems(workspaceSlug);

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r bg-card transition-all duration-200',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex h-full flex-col">
        <div
          className={cn(
            'flex h-14 items-center border-b px-4',
            sidebarCollapsed ? 'justify-center' : 'justify-start gap-2'
          )}
        >
          <Layers className="h-6 w-6 text-primary" />
          {!sidebarCollapsed && <span className="font-semibold">Kraivor</span>}
        </div>

        <nav className="flex-1 space-y-1 p-2">
          {navItems.map(item => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                href={item.path}
                className={cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200 border',
                  
                  active
                    ? 'bg-primary text-primary-foreground border-primary/20 shadow-sm'
                    : 'border-transparent text-muted-foreground hover:bg-primary/10 hover:text-foreground',

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
          {bottomNavItems.map(item => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                href={item.path}
                className={cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200 border',
                  
                  active
                    ? 'bg-primary text-primary-foreground border-primary/20 shadow-sm'
                    : 'border-transparent text-muted-foreground hover:bg-primary/10 hover:text-foreground',

                  sidebarCollapsed && 'justify-center px-2'
                )}    
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
          <Button
            variant="ghost"
            size="sm"
            className={cn('w-full mt-2', sidebarCollapsed && 'px-2')}
            onClick={toggleSidebarCollapse}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
            {!sidebarCollapsed && <span className="ml-2">Collapse</span>}
          </Button>
        </div>
      </div>
    </aside>
  );
}
