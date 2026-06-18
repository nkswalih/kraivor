'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useUIStore } from '@/lib/stores';
import { Search, Hash, BookOpen, GitBranch, Settings, MessageSquare, Inbox, Box } from 'lucide-react';

const defaultActions = [
  { id: 'chat', label: 'Go to Chat', icon: MessageSquare, href: (ws: string) => `/${ws}/chat` },
  { id: 'knowledge', label: 'Go to Knowledge', icon: BookOpen, href: (ws: string) => `/${ws}/knowledge` },
  { id: 'repos', label: 'Go to Repositories', icon: GitBranch, href: (ws: string) => `/${ws}/repos` },
  { id: 'inbox', label: 'Go to Inbox', icon: Inbox, href: (ws: string) => `/${ws}/inbox` },
  { id: 'settings', label: 'Go to Settings', icon: Settings, href: (ws: string) => `/${ws}/settings` },
];

export function CommandPalette({ workspaceSlug }: { workspaceSlug: string }) {
  const router = useRouter();
  const { isCommandPaletteOpen, setCommandPaletteOpen } = useUIStore();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!isCommandPaletteOpen);
        setQuery('');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isCommandPaletteOpen, setCommandPaletteOpen]);

  useEffect(() => {
    if (isCommandPaletteOpen) {
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isCommandPaletteOpen]);

  const handleClose = useCallback(() => {
    setCommandPaletteOpen(false);
    setQuery('');
  }, [setCommandPaletteOpen]);

  const filtered = defaultActions.filter(
    (a) => a.label.toLowerCase().includes(query.toLowerCase()),
  );

  const handleSelect = (action: typeof defaultActions[0]) => {
    handleClose();
    router.push(action.href(workspaceSlug));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      handleSelect(filtered[selectedIndex]);
    } else if (e.key === 'Escape') {
      handleClose();
    }
  };

  if (!isCommandPaletteOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm animate-fade-in"
      onMouseDown={(e) => { if (e.target === e.currentTarget) handleClose(); }}
    >
      <div className="w-full max-w-[560px] bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl overflow-hidden animate-scale-in">
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[#27272A]">
          <Search className="w-4 h-4 text-text-tertiary shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search..."
            className="flex-1 bg-transparent border-none text-[14px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none"
          />
          <kbd className="text-[10px] text-text-tertiary border border-[#27272A] px-1.5 py-0.5 rounded">
            ESC
          </kbd>
        </div>

        <div className="px-2 py-2 max-h-[300px] overflow-y-auto">
          <p className="px-3 py-1.5 text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
            Navigation
          </p>
          {filtered.map((action, idx) => (
            <button
              key={action.id}
              onClick={() => handleSelect(action)}
              onMouseEnter={() => setSelectedIndex(idx)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-[13px] transition-colors ${
                idx === selectedIndex
                  ? 'bg-venom-yellow/10 text-[#FAFAFA]'
                  : 'text-text-secondary hover:bg-krait-surface2'
              }`}
            >
              <action.icon className="w-4 h-4 shrink-0" />
              <span>{action.label}</span>
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="px-3 py-4 text-center text-[13px] text-text-tertiary">No results for &quot;{query}&quot;</p>
          )}
        </div>
      </div>
    </div>
  );
}
