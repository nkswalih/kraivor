'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useUIStore, useAuthStore } from '@/lib/stores';
import { useSearch } from '@/lib/hooks/use-search';
import {
  Search,
  Hash,
  BookOpen,
  GitBranch,
  Settings,
  MessageSquare,
  Inbox,
  Box,
  Users,
  FileText,
} from 'lucide-react';

const defaultActions = [
  { id: 'chat', label: 'Go to Chat', icon: MessageSquare, href: (ws: string) => `/${ws}/chat` },
  {
    id: 'knowledge',
    label: 'Go to Knowledge',
    icon: BookOpen,
    href: (ws: string) => `/${ws}/knowledge`,
  },
  {
    id: 'repos',
    label: 'Go to Repositories',
    icon: GitBranch,
    href: (ws: string) => `/${ws}/repos`,
  },
  { id: 'inbox', label: 'Go to Inbox', icon: Inbox, href: (ws: string) => `/${ws}/inbox` },
  {
    id: 'settings',
    label: 'Go to Settings',
    icon: Settings,
    href: (ws: string) => `/${ws}/settings`,
  },
];

const typeIcons: Record<string, typeof Box> = {
  project: Hash,
  task: FileText,
  knowledge: BookOpen,
  knowledge_asset: FileText,
  repository: GitBranch,
  notification: Inbox,
  chat: MessageSquare,
  profile: Users,
};

const typeLabels: Record<string, string> = {
  project: 'Project',
  task: 'Task',
  knowledge: 'Knowledge Space',
  knowledge_asset: 'Asset',
  repository: 'Repository',
  notification: 'Notification',
  chat: 'Chat Message',
  profile: 'Profile',
};

export function CommandPalette({ workspaceSlug }: { workspaceSlug: string }) {
  const router = useRouter();
  const { isCommandPaletteOpen, setCommandPaletteOpen } = useUIStore();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showResults, setShowResults] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsContainerRef = useRef<HTMLDivElement>(null);

  const workspaces = useAuthStore(s => s.workspaces);
  const workspaceId =
    workspaces.find((w: { slug: string }) => w.slug === workspaceSlug)?.id ?? null;

  const { query, setQuery, results, totalResults, isLoading, clearSearch } = useSearch(
    workspaceId,
    250
  );

  const filtered = defaultActions.filter(a => a.label.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isCommandPaletteOpen) {
          clearSearch();
        }
        setCommandPaletteOpen(!isCommandPaletteOpen);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isCommandPaletteOpen, setCommandPaletteOpen, clearSearch]);

  useEffect(() => {
    if (isCommandPaletteOpen) {
      setSelectedIndex(0);
      setShowResults(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isCommandPaletteOpen]);

  useEffect(() => {
    if (query.length >= 2) {
      setShowResults(true);
      setSelectedIndex(0);
    } else {
      setShowResults(false);
    }
  }, [query]);

  useEffect(() => {
    if (resultsContainerRef.current && selectedIndex >= 0) {
      const items =
        resultsContainerRef.current.querySelectorAll<HTMLButtonElement>('[data-search-item]');
      items[selectedIndex - filtered.length]?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex, results, filtered.length]);

  const handleClose = useCallback(() => {
    setCommandPaletteOpen(false);
    clearSearch();
  }, [setCommandPaletteOpen, clearSearch]);

  const handleSelect = (action: (typeof defaultActions)[0]) => {
    handleClose();
    router.push(action.href(workspaceSlug));
  };

  const handleSearchSelect = (result: (typeof results)[0]) => {
    handleClose();
    router.push(result.url);
  };

  const totalItems = filtered.length + (showResults ? results.length : 0);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, totalItems - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      const navCount = filtered.length;
      if (selectedIndex < navCount && filtered[selectedIndex]) {
        handleSelect(filtered[selectedIndex]);
      } else if (showResults) {
        const resultIndex = selectedIndex - navCount;
        if (results[resultIndex]) {
          handleSearchSelect(results[resultIndex]);
        }
      }
    } else if (e.key === 'Escape') {
      handleClose();
    }
  };

  if (!isCommandPaletteOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm animate-fade-in"
      onMouseDown={e => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="w-full max-w-[560px] bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl overflow-hidden animate-scale-in">
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[#27272A]">
          <Search className="w-4 h-4 text-text-tertiary shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search..."
            className="flex-1 bg-transparent border-none text-[14px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none"
          />
          {isLoading && (
            <div className="w-4 h-4 border-2 border-text-tertiary border-t-transparent rounded-full animate-spin" />
          )}
          <kbd className="text-[10px] text-text-tertiary border border-[#27272A] px-1.5 py-0.5 rounded">
            ESC
          </kbd>
        </div>

        <div ref={resultsContainerRef} className="px-2 py-2 max-h-[400px] overflow-y-auto">
          {query.length < 2 && (
            <p className="px-3 py-1.5 text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
              Navigation
            </p>
          )}
          {filtered.map((action, idx) => (
            <button
              key={action.id}
              data-search-item
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

          {showResults && (
            <>
              <p className="px-3 py-1.5 mt-1 text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
                Results{totalResults > 0 ? ` (${totalResults})` : ''}
              </p>
              {results.map((result, idx) => {
                const globalIdx = filtered.length + idx;
                const Icon = typeIcons[result.type] || Box;
                return (
                  <button
                    key={`${result.type}-${result.id}`}
                    data-search-item
                    onClick={() => handleSearchSelect(result)}
                    onMouseEnter={() => setSelectedIndex(globalIdx)}
                    className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left text-[13px] transition-colors ${
                      globalIdx === selectedIndex
                        ? 'bg-venom-yellow/10 text-[#FAFAFA]'
                        : 'text-text-secondary hover:bg-krait-surface2'
                    }`}
                  >
                    <Icon className="w-4 h-4 mt-0.5 shrink-0 text-text-tertiary" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[#FAFAFA]">{result.title}</div>
                      {result.description && (
                        <div className="truncate text-[11px] text-text-tertiary mt-0.5">
                          {result.description}
                        </div>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-krait-surface3 text-text-tertiary">
                          {typeLabels[result.type] || result.type}
                        </span>
                        {result.metadata?.status != null && (
                          <span className="text-[10px] text-text-tertiary capitalize">{`${result.metadata.status}`}</span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
              {!isLoading && results.length === 0 && query.length >= 2 && (
                <p className="px-3 py-4 text-center text-[13px] text-text-tertiary">
                  No results for &quot;{query}&quot;
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
