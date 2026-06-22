'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { Check, Plus, ChevronsUpDown } from 'lucide-react';
import { CreateWorkspaceDialog } from '@/components/features/create-workspace-dialog';

export function WorkspaceSwitcher({ workspaceSlug }: { workspaceSlug: string }) {
  const router = useRouter();
  const { workspaces, workspaceId, setWorkspace } = useAuthStore();
  const [open, setOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = workspaces.find((w: any) => w.slug === workspaceSlug) ?? workspaces[0];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSwitch = (ws: any) => {
    setWorkspace(ws.id, ws.slug);
    setOpen(false);
    router.push(`/${ws.slug}`);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="h-12 w-full flex items-center justify-between px-4 border-b border-[#27272A] hover:bg-[#18181B] transition-colors"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-5 h-5 bg-[#6366F1] rounded-[4px] flex items-center justify-center text-white font-bold text-[11px] shrink-0">
            {(current?.name ?? workspaceSlug ?? '?').charAt(0).toUpperCase()}
          </div>
          <span className="font-medium text-[#FAFAFA] text-[13px] tracking-wide truncate">
            {current?.name ?? workspaceSlug ?? 'Select workspace'}
          </span>
        </div>
        <ChevronsUpDown className="w-4 h-4 text-[#A1A1AA] shrink-0" />
      </button>

      {open && (
        <div className="absolute left-2 right-2 top-full mt-1 bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl z-50 overflow-hidden animate-scale-in origin-top">
          <div className="px-3 py-2 border-b border-[#27272A]">
            <span className="text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
              Workspaces
            </span>
          </div>
          <div className="py-1 max-h-[200px] overflow-y-auto">
            {workspaces.length === 0 && (
              <p className="px-3 py-2 text-[12px] text-text-tertiary">No workspaces</p>
            )}
            {workspaces.map((ws: any) => (
              <button
                key={ws.id}
                onClick={() => handleSwitch(ws)}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-[13px] text-text-secondary hover:bg-krait-surface2 hover:text-[#FAFAFA] transition-colors text-left"
              >
                <div className="w-5 h-5 rounded-[4px] bg-[#27272A] flex items-center justify-center text-[10px] font-bold text-[#FAFAFA] shrink-0">
                  {ws.name.charAt(0).toUpperCase()}
                </div>
                <span className="truncate flex-1">{ws.name}</span>
                {ws.id === workspaceId && (
                  <Check className="w-3.5 h-3.5 text-venom-yellow shrink-0" />
                )}
              </button>
            ))}
          </div>
          <div className="border-t border-[#27272A] py-1">
            <button
              onClick={() => {
                setOpen(false);
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

      <CreateWorkspaceDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={slug => router.push(`/${slug}`)}
      />
    </div>
  );
}
