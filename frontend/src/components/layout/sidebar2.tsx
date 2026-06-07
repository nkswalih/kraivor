'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/hooks';
import { getInitials } from '@/lib/utils';
import { 
  Home, GitBranch, Activity, Sparkles, Edit3, 
  KanbanSquare, CheckSquare, MessageSquare, Globe, 
  Bell, Settings, ChevronsUpDown, LogOut 
} from 'lucide-react';
import { cn } from '@/lib/utils';

export function Sidebar({ workspaceSlug }: { workspaceSlug: string }) {
  const pathname = usePathname();
  // Bring in the dynamic user data and logout function
  const { user, logout } = useAuth();

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
    <aside className="w-[240px] flex-shrink-0 flex flex-col bg-[#111113] border-r border-[#27272A] h-full select-none">
      
      {/* Workspace Switcher */}
      <div className="h-12 flex items-center justify-between px-4 border-b border-[#27272A] hover:bg-[#18181B] cursor-pointer transition-colors">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 bg-[#6366F1] rounded-[4px] flex items-center justify-center text-white font-bold text-[11px]">
            {/* You can also make this dynamic based on workspace name */}
            {workspaceSlug.charAt(0).toUpperCase()}
          </div>
          <span className="font-medium text-[#FAFAFA] text-[13px] tracking-wide truncate">
            {workspaceSlug}
          </span>
        </div>
        <ChevronsUpDown className="w-4 h-4 text-[#A1A1AA] shrink-0" />
      </div>

      {/* Main Navigation */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {navItems.map((item) => {
          const isActive = item.href === `/${workspaceSlug}` 
            ? pathname === item.href 
            : pathname.startsWith(item.href);

          return (
            <Link 
              key={item.name} 
              href={item.href} 
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-1.5 rounded-[6px] transition-colors text-[13px] font-medium",
                isActive 
                  ? "bg-[#18181B] text-[#FAFAFA]" 
                  : "text-[#A1A1AA] hover:bg-[#18181B]/50 hover:text-[#FAFAFA]"
              )}
            >
              <item.icon className={cn("w-4 h-4", isActive ? "text-[#FAFAFA]" : "text-[#A1A1AA]")} />
              {item.name}
              
              {item.name === 'Chat' && (
                <span className="ml-auto flex h-4 w-4 items-center justify-center rounded-full bg-[#6366F1] text-[10px] text-white">
                  3
                </span>
              )}
            </Link>
          );
        })}
      </div>
      
      {/* Bottom Section */}
      <div className="p-2 border-t border-[#27272A] space-y-0.5">
         <Link href={`/${workspaceSlug}/notifications`} className="flex items-center justify-between px-2.5 py-1.5 rounded-[6px] text-[#A1A1AA] hover:bg-[#18181B]/50 hover:text-[#FAFAFA] transition-colors text-[13px] font-medium">
            <div className="flex items-center gap-2.5">
              <Bell className="w-4 h-4" />
              Notifications
            </div>
            <div className="w-1.5 h-1.5 bg-[#EF4444] rounded-full"></div>
          </Link>
          
         <Link href={`/${workspaceSlug}/settings`} className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-[6px] text-[#A1A1AA] hover:bg-[#18181B]/50 hover:text-[#FAFAFA] transition-colors text-[13px] font-medium">
            <Settings className="w-4 h-4" />
            Settings
          </Link>

          {/* DYNAMIC User Profile Block */}
          <div className="mt-2 pt-2 border-t border-[#27272A]">
            <div className="flex items-center gap-3 px-2 py-1.5 rounded-[6px] hover:bg-[#18181B] transition-colors group">
              
              {/* Avatar: Uses image if available, otherwise falls back to initials */}
              {user?.avatar_url ? (
                <img 
                  src={user.avatar_url} 
                  alt={user.name || 'User'} 
                  className="w-8 h-8 rounded-[4px] object-cover shrink-0 border border-[#27272A]"
                />
              ) : (
                <div className="w-8 h-8 rounded-[4px] bg-[#27272A] border border-[#27272A] flex items-center justify-center text-[11px] font-medium text-[#FAFAFA] shrink-0">
                  {user?.name ? getInitials(user.name) : 'U'}
                </div>
              )}

              {/* User Info */}
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-[#FAFAFA] truncate leading-tight">
                  {user?.name || 'Loading...'}
                </p>
                <p className="text-[11px] text-[#A1A1AA] truncate leading-tight mt-0.5">
                  {user?.email || ''}
                </p>
              </div>

              {/* Logout Action (Reveals on Hover) */}
              <button 
                onClick={() => logout()}
                className="p-1.5 text-[#A1A1AA] hover:text-[#EF4444] opacity-0 group-hover:opacity-100 transition-all shrink-0 rounded-[4px] hover:bg-[#EF4444]/10"
                title="Log Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
      </div>
    </aside>
  );
}