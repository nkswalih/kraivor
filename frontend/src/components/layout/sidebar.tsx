'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/lib/hooks';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useChatStore } from '@/lib/stores/chat-store';
import { useUIStore } from '@/lib/stores/ui-store';
import { profileEndpoints, chatEndpoints } from '@/lib/api/endpoints';
import { getInitials, cn } from '@/lib/utils';
import {
  Home,
  GitBranch,
  Activity,
  Sparkles,
  Edit3,
  KanbanSquare,
  CheckSquare,
  MessageSquare,
  Globe,
  Inbox,
  Settings,
  LogOut,
  Building2,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

export function Sidebar({ workspaceSlug }: { workspaceSlug: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const workspaceId = useAuthStore(s => s.workspaceId);
  const collapsed = useUIStore(s => s.sidebarCollapsed);
  const toggleCollapse = useUIStore(s => s.toggleSidebarCollapse);

  const { data: profile } = useQuery({
    queryKey: ['my-profile'],
    queryFn: () => profileEndpoints.getMyProfile(),
    staleTime: 30_000,
  });

  const bestAvatar = profile?.avatar_url || profile?.user_avatar_url || user?.avatar_url || null;

  /* ─── Fetch rooms to sync unread counts ────────────────────── */
  const { data: rooms } = useQuery({
    queryKey: ['rooms', workspaceId],
    queryFn: () => chatEndpoints.listRooms(workspaceId!),
    enabled: !!workspaceId,
  });
  const roomsList = Array.isArray(rooms) ? rooms : (rooms?.results ?? []);

  const syncUnread = useChatStore(s => s.syncUnreadFromRooms);
  useEffect(() => {
    if (roomsList.length) syncUnread(roomsList);
  }, [roomsList, syncUnread]);

  const totalUnread = useChatStore(s => s.totalUnread());

  const navItems = [
    { name: 'Home', icon: Home, href: `/${workspaceSlug}` },
    { name: 'Repositories', icon: GitBranch, href: `/${workspaceSlug}/repositories` },
    { name: 'Analysis', icon: Activity, href: `/${workspaceSlug}/analysis` },
    { name: 'AI Workspace', icon: Sparkles, href: `/${workspaceSlug}/ai` },
    { name: 'Knowledge', icon: Edit3, href: `/${workspaceSlug}/knowledge` },
    { name: 'Projects', icon: KanbanSquare, href: `/${workspaceSlug}/projects` },
    { name: 'Tasks', icon: CheckSquare, href: `/${workspaceSlug}/tasks` },
    { name: 'Chat', icon: MessageSquare, href: `/${workspaceSlug}/chat` },
    { name: 'Community', icon: Globe, href: `/${workspaceSlug}/community` },
  ];

  return (
    <aside
      className={`${collapsed ? 'w-[60px]' : 'w-[240px]'} flex-shrink-0 flex flex-col bg-krait-obsidian border-r border-krait-border h-full select-none transition-all duration-200`}
    >
      {/* Main Navigation */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {navItems.map(item => {
          const isActive =
            item.href === `/${workspaceSlug}`
              ? pathname === item.href
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.name}
              href={item.href}
              title={collapsed ? item.name : undefined}
              className={cn(
                'flex items-center rounded-[6px] transition-colors text-[13px] font-medium',
                collapsed ? 'justify-center px-0 py-2 relative' : 'gap-2.5 px-2.5 py-1.5',
                isActive
                  ? 'bg-krait-surface1 text-text-primary'
                  : 'text-text-secondary hover:bg-krait-surface1/50 hover:text-text-primary'
              )}
            >
              <item.icon
                className={cn('w-4 h-4 shrink-0', isActive ? 'text-text-primary' : 'text-text-secondary')}
              />
              <span className={collapsed ? 'hidden' : ''}>{item.name}</span>

              {item.name === 'Chat' &&
                totalUnread > 0 &&
                (collapsed ? (
                  <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-[#EF4444]" />
                ) : (
                  <span className="ml-auto flex h-4 min-w-4 items-center justify-center rounded-full bg-[#EF4444] text-[10px] font-extrabold text-white px-1">
                    {totalUnread > 99 ? '99+' : totalUnread}
                  </span>
                ))}
            </Link>
          );
        })}

        <div className="my-3 border-t border-krait-border" />
      </div>

      {/* Bottom Section */}
      <div className="p-2 border-t border-krait-border space-y-0.5">
        <Link
          href={`/${workspaceSlug}/settings/workspace`}
          title={collapsed ? 'Workspaces' : undefined}
          className={cn(
            'flex items-center rounded-[6px] text-text-secondary hover:bg-krait-surface1/50 hover:text-text-primary transition-colors text-[13px] font-medium',
            collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-2.5 py-1.5'
          )}
        >
          <Building2 className="w-4 h-4 shrink-0" />
          <span className={collapsed ? 'hidden' : ''}>Workspaces</span>
        </Link>

        <Link
          href={`/${workspaceSlug}/inbox`}
          title={collapsed ? 'Inbox' : undefined}
          className={cn(
            'flex items-center rounded-[6px] text-text-secondary hover:bg-krait-surface1/50 hover:text-text-primary transition-colors text-[13px] font-medium',
            collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-2.5 py-1.5'
          )}
        >
          <Inbox className="w-4 h-4 shrink-0" />
          <span className={collapsed ? 'hidden' : ''}>Inbox</span>
          {!collapsed && <div className="ml-auto w-1.5 h-1.5 bg-[#EF4444] rounded-full" />}
        </Link>

        <Link
          href={`/${workspaceSlug}/settings`}
          title={collapsed ? 'Settings' : undefined}
          className={cn(
            'flex items-center rounded-[6px] text-text-secondary hover:bg-krait-surface1/50 hover:text-text-primary transition-colors text-[13px] font-medium',
            collapsed ? 'justify-center px-0 py-2' : 'gap-2.5 px-2.5 py-1.5'
          )}
        >
          <Settings className="w-4 h-4 shrink-0" />
          <span className={collapsed ? 'hidden' : ''}>Settings</span>
        </Link>

        {/* Separator */}
        {!collapsed && <div className="mt-2 pt-2 border-t border-krait-border" />}

        {/* User Profile Block */}
        <div className={collapsed ? '' : 'mt-2'}>
          <button
            onClick={() => {
              if (profile?.username) router.push(`/${workspaceSlug}/profile/${profile.username}`);
            }}
            title={collapsed ? profile?.display_name || user?.name || 'Profile' : undefined}
            className={cn(
              'w-full flex items-center rounded-[6px] hover:bg-krait-surface1 transition-colors group text-left',
              collapsed ? 'justify-center py-2' : 'gap-3 px-2 py-1.5'
            )}
          >
            {bestAvatar ? (
              <img
                src={bestAvatar}
                alt={user?.name || 'User'}
                className={cn(
                  'shrink-0 object-cover border border-krait-border',
                  collapsed ? 'w-8 h-8 rounded-full' : 'w-8 h-8 rounded-[4px]'
                )}
              />
            ) : (
              <div
                className={cn(
                  'bg-krait-surface3 border border-krait-border flex items-center justify-center text-[11px] font-medium text-text-primary shrink-0',
                  collapsed ? 'w-8 h-8 rounded-full' : 'w-8 h-8 rounded-[4px]'
                )}
              >
                {user?.name ? getInitials(user.name) : 'U'}
              </div>
            )}

            {!collapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium text-text-primary truncate leading-tight">
                    {profile?.display_name || user?.name || 'Loading...'}
                  </p>
                  <p className="text-[11px] text-text-secondary truncate leading-tight mt-0.5">
                    {user?.email || ''}
                  </p>
                </div>

                <span
                  onClick={e => {
                    e.stopPropagation();
                    logout();
                  }}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.stopPropagation();
                      logout();
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  className="p-1.5 text-[#A1A1AA] hover:text-[#EF4444] opacity-0 group-hover:opacity-100 transition-all shrink-0 rounded-[4px] hover:bg-[#EF4444]/10 cursor-pointer"
                  title="Log Out"
                >
                  <LogOut className="w-4 h-4" />
                </span>
              </>
            )}
          </button>
        </div>

        {/* Toggle Collapse Button */}
        <button
          onClick={toggleCollapse}
          className="w-full flex items-center justify-center py-2 rounded-[6px] text-text-secondary hover:bg-krait-surface1/50 hover:text-text-primary transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>
    </aside>
  );
}
