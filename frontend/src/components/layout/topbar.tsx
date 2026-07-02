'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Search, ChevronDown, Check, Plus } from 'lucide-react';
import { useUIStore } from '@/lib/stores';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useAiConversationStore } from '@/lib/stores/ai-conversation-store';
import { useBreadcrumbStore } from '@/lib/stores/breadcrumb-store';
import { CommandPalette } from '@/components/features/command-palette';
import { InboxPopover } from '@/components/features/inbox-popover';
import { CreateWorkspaceDialog } from '@/components/features/create-workspace-dialog';

const ROUTE_LABELS: Record<string, string> = {
  '': 'Home',
  chat: 'Chat',
  repositories: 'Repositories',
  analysis: 'Analysis',
  ai: 'AI Workspace',
  knowledge: 'Knowledge',
  projects: 'Projects',
  tasks: 'Tasks',
  community: 'Community',
  inbox: 'Inbox',
  settings: 'Settings',
  profile: 'Profile',
};

export function Topbar({ workspaceSlug }: { workspaceSlug: string }) {
  const router = useRouter();

  const setCommandPaletteOpen = useUIStore(state => state.setCommandPaletteOpen);

  const { workspaces, workspaceId, setWorkspace } = useAuthStore();
  const { activeConversationId, clear: clearAiStore } = useAiConversationStore();
  const detailTitle = useBreadcrumbStore(s => s.detailTitle);
  const pathname = usePathname();
  const [wsOpen, setWsOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const wsRef = useRef<HTMLDivElement>(null);

  const workspace = useMemo(
    () => workspaces.find((w: { slug: string }) => w.slug === workspaceSlug),
    [workspaces, workspaceSlug]
  );

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wsRef.current && !wsRef.current.contains(e.target as Node)) setWsOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  /* Clear AI conversation state when leaving AI routes */
  const isAiRoute = pathname.startsWith(`/${workspaceSlug}/ai`);
  useEffect(() => {
    if (!isAiRoute && activeConversationId) {
      clearAiStore();
    }
  }, [isAiRoute, activeConversationId, clearAiStore]);

  /* Derive a human-readable page label from the path */
  const routeLabel = useMemo(() => {
    const segments = pathname.split('/').filter(Boolean);
    if (segments.length <= 1) return 'Home';
    const sub = segments[1];
    const sub2 = segments[2];
    if (sub === 'settings') {
      if (sub2 === 'workspace') return 'Workspaces';
      return 'Settings';
    }
    if (sub === 'chat' && sub2) return 'Chat';
    if (sub === 'knowledge' && sub2) return 'Knowledge';
    return ROUTE_LABELS[sub] ?? sub.charAt(0).toUpperCase() + sub.slice(1);
  }, [pathname]);

  const segments = pathname.split('/').filter(Boolean);
  const route = segments[1] || '';
  const hasDetail = (segments.length >= 3 && !!detailTitle) || (route === 'ai' && !!detailTitle);
  const workspaceName = workspace?.name || workspaceSlug;

  return (
    <header className="h-12 border-b border-krait-border flex items-center px-4 bg-krait-void shrink-0 gap-4">
      {/* Left — workspace switcher + route */}
      <div className="flex items-center gap-1 min-w-0">
        <div ref={wsRef} className="relative">
          <button
            onClick={() => setWsOpen(!wsOpen)}
            className="flex items-center gap-1.5 px-2 py-1 rounded-[6px] hover:bg-krait-surface1 transition-colors text-[13px] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
          >
            <div className="w-5 h-5 bg-primary shadow-lg shadow-primary/20 rounded-[4px] flex items-center justify-center text-black font-bold text-[10px] shrink-0">
              {workspaceName.charAt(0).toUpperCase()}
            </div>
            <span className="text-text-secondary hover:text-text-primary transition-colors truncate max-w-[120px]">
              {workspaceName}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-text-secondary shrink-0" />
          </button>

          {wsOpen && (
            <div className="absolute left-0 top-full mt-1 w-[220px] bg-krait-surface2 border border-krait-border rounded-xl shadow-2xl z-50 overflow-hidden animate-scale-in origin-top">
              <div className="px-3 py-2 border-b border-krait-border">
                <span className="text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
                  Workspaces
                </span>
              </div>
              <div className="py-1 max-h-[200px] overflow-y-auto">
                {workspaces.length === 0 && (
                  <p className="px-3 py-2 text-[12px] text-text-tertiary">No workspaces</p>
                )}
                {(workspaces as Array<{ id: string; slug: string; name: string }>).map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setWorkspace(ws.id, ws.slug);
                      setWsOpen(false);
                      router.push(`/${ws.slug}`);
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-[13px] text-text-secondary hover:bg-krait-surface2 hover:text-text-primary transition-colors text-left"
                  >
                    <div className="w-5 h-5 rounded-[4px] bg-krait-surface3 flex items-center justify-center text-[10px] font-bold text-text-primary shrink-0">
                      {ws.name.charAt(0).toUpperCase()}
                    </div>
                    <span className="truncate flex-1">{ws.name}</span>
                    {ws.id === workspaceId && (
                      <Check className="w-3.5 h-3.5 text-venom-yellow shrink-0" />
                    )}
                  </button>
                ))}
              </div>
              <div className="border-t border-krait-border py-1">
                <button
                  onClick={() => {
                    setWsOpen(false);
                    setShowCreate(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-[13px] text-venom-yellow hover:bg-krait-surface2 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Create workspace
                </button>
              </div>
            </div>
          )}
        </div>

        <span className="text-krait-border mx-1 shrink-0">/</span>
        <Link
          href={`/${workspaceSlug}/${route}`}
          className="text-text-secondary hover:text-text-primary transition-colors text-[13px] truncate hover:bg-krait-surface1 rounded-[4px] px-1 -mx-1"
        >
          {routeLabel}
        </Link>
        {hasDetail && (
          <>
            <span className="text-krait-border mx-1 shrink-0">/</span>
            <span className="text-text-primary font-semibold text-[13px] truncate max-w-[200px]">
              {detailTitle}
            </span>
          </>
        )}
      </div>

      {/* Spacer pushes everything else to the right */}
      <div className="flex-1" />

      {/* Right Side — Search + Context Panel Icons */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Search */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-2.5 py-1.5 bg-krait-obsidian border border-krait-border rounded-md text-text-secondary hover:border-krait-borderHi hover:text-text-primary transition-colors w-64 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="text-[12px] flex-1 text-left">Search...</span>
          <span className="text-[10px] bg-krait-surface1 border border-krait-border px-1.5 py-0.5 rounded text-text-tertiary font-medium shrink-0">
            ⌘K
          </span>
        </button>

        {/* Vertical Divider */}
        <div className="w-px h-4 bg-krait-border mx-1" />

        {/* Icons */}
        <div className="flex items-center gap-1.5">
          <InboxPopover />

          {/* VS Code Style Right Panel Toggle */}
          {/* <button
            onClick={toggleRightPanel}
            className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-krait-border/50 rounded-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
            title="Toggle Context Panel (VS Code style Chat/Context)"
          >
            <PanelRight className="w-4 h-4" />
          </button>  */}
        </div>
      </div>

      {/* Modals */}
      <CreateWorkspaceDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={slug => router.push(`/${slug}`)}
      />

      <CommandPalette workspaceSlug={workspaceSlug} />
    </header>
  );
}
