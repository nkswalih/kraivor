'use client';

import { Search, Sidebar as SidebarIcon, PanelRight } from 'lucide-react';
import { useUIStore } from '@/lib/stores';

export function Topbar({ workspaceSlug }: { workspaceSlug: string }) {
  const toggleRightPanel = useUIStore((state) => state.toggleRightPanel);

  return (
    <header className="h-12 border-b border-[#27272A] flex items-center justify-between px-4 bg-[#0A0A0B] shrink-0">
      
      {/* Breadcrumbs / View Title */}
      <div className="flex items-center gap-3">
        <button className="text-[#A1A1AA] hover:text-[#FAFAFA] transition-colors">
          <SidebarIcon className="w-4 h-4" />
        </button>
        <div className="flex items-center text-[13px]">
          <span className="text-[#A1A1AA]">Kraivor Inc</span>
          <span className="text-[#27272A] mx-2">/</span>
          <span className="text-[#FAFAFA] font-medium">Architecture Review</span>
        </div>
      </div>

      {/* Command Search */}
      <button className="flex items-center gap-2 px-3 py-1.5 bg-[#111113] border border-[#27272A] rounded-[6px] text-[#A1A1AA] hover:border-[#A1A1AA]/50 transition-colors w-64">
        <Search className="w-3.5 h-3.5" />
        <span className="text-[12px]">Type command or search...</span>
        <span className="ml-auto text-[10px] border border-[#27272A] px-1 rounded">⌘K</span>
      </button>

      {/* Right Actions */}
      <div className="flex items-center gap-3">
        <button 
          onClick={toggleRightPanel}
          className="text-[#A1A1AA] hover:text-[#FAFAFA] transition-colors"
          title="Toggle Context Panel"
        >
          <PanelRight className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}