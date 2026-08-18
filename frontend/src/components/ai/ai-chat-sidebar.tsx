'use client';

import { useState, useMemo } from 'react';
import { 
  Search, 
  Plus, 
  MessagesSquare, 
  Pin, 
  PinOff, 
  Pencil, 
  Trash2, 
  Check, 
  X,
  Clock,
  MoreHorizontal
} from 'lucide-react';
import { aiApi } from '@/lib/api/ai-api';
import type { ConversationSummary } from '@/lib/api/ai-api';
import { cn } from '@/lib/utils';

interface AiChatSidebarProps {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onRefresh: () => void;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);
  const diffMonths = Math.floor(diffDays / 30);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffWeeks < 4) return `${diffWeeks}w ago`;
  return `${diffMonths}mo ago`;
}

export function AiChatSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onRefresh,
}: AiChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingConv, setEditingConv] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [hoveredConv, setHoveredConv] = useState<string | null>(null);

  const sorted = useMemo(() => {
    const filtered = conversations.filter(conv =>
      conv.title.toLowerCase().includes(searchQuery.toLowerCase())
    );
    return filtered.sort((a, b) => {
      if (a.is_pinned && !b.is_pinned) return -1;
      if (!a.is_pinned && b.is_pinned) return 1;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [conversations, searchQuery]);

  const handleRename = async (convId: string, newTitle: string) => {
    const trimmed = newTitle.trim();
    if (trimmed && trimmed !== conversations.find(c => c.id === convId)?.title) {
      await aiApi.updateConversation(convId, { title: trimmed });
      onRefresh();
    }
    setEditingConv(null);
  };

  const handleTogglePin = async (convId: string, currentlyPinned: boolean) => {
    await aiApi.updateConversation(convId, { is_pinned: !currentlyPinned });
    onRefresh();
  };

  const handleDelete = async (convId: string) => {
    if (confirm('Delete this conversation?')) {
      await aiApi.deleteConversation(convId);
      onRefresh();
    }
  };

  return (
    <div className="w-[260px] flex-shrink-0 flex flex-col bg-krait-obsidian border-r border-krait-border h-full">
      {/* Header */}
      <div className="p-3 border-b border-krait-border">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-krait-surface2 hover:bg-krait-surface3 border border-krait-border/50 rounded-lg transition-colors text-[13px] font-medium text-text-primary"
        >
          <Plus className="w-4 h-4" strokeWidth={2} />
          New Chat
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            className="w-full pl-8 pr-3 py-1.5 bg-krait-surface2 border border-krait-border/50 rounded-md text-[12px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/40 transition-colors"
          />
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2 py-1">
        {sorted.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <MessagesSquare className="w-8 h-8 text-text-tertiary mx-auto mb-2" strokeWidth={1.5} />
            <p className="text-[12px] text-text-tertiary">
              {searchQuery ? 'No matching chats' : 'No conversations yet'}
            </p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {sorted.map((conv) => (
              <div
                key={conv.id}
                className={cn(
                  'group relative flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors',
                  activeConversationId === conv.id
                    ? 'bg-krait-surface1 text-text-primary'
                    : 'text-text-secondary hover:bg-krait-surface2'
                )}
                onClick={() => onSelectConversation(conv.id)}
                onMouseEnter={() => setHoveredConv(conv.id)}
                onMouseLeave={() => setHoveredConv(null)}
              >
                {editingConv === conv.id ? (
                  <div className="flex items-center gap-1 flex-1 min-w-0">
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="flex-1 bg-transparent border-b border-venom-yellow/50 text-[12px] text-text-primary outline-none min-w-0"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRename(conv.id, editValue);
                        if (e.key === 'Escape') setEditingConv(null);
                      }}
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRename(conv.id, editValue);
                      }}
                      className="p-0.5 rounded text-text-secondary hover:text-text-primary"
                    >
                      <Check className="w-3 h-3" strokeWidth={2} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingConv(null);
                      }}
                      className="p-0.5 rounded text-text-tertiary hover:text-text-secondary"
                    >
                      <X className="w-3 h-3" strokeWidth={2} />
                    </button>
                  </div>
                ) : (
                  <>
                    <MessagesSquare
                      className={cn(
                        'w-4 h-4 shrink-0',
                        activeConversationId === conv.id ? 'text-venom-yellow' : 'text-text-tertiary'
                      )}
                      strokeWidth={1.5}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-[12px] font-medium truncate">{conv.title}</div>
                      <div className="flex items-center gap-1 text-[10px] text-text-tertiary">
                        <Clock className="w-2.5 h-2.5" strokeWidth={2} />
                        {formatRelativeTime(conv.updated_at)}
                        <span className="mx-0.5">·</span>
                        {conv.message_count} {conv.message_count === 1 ? 'message' : 'messages'}
                      </div>
                    </div>
                  </>
                )}

                {/* Actions */}
                {editingConv !== conv.id && hoveredConv === conv.id && (
                  <div className="flex items-center gap-0.5 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingConv(conv.id);
                        setEditValue(conv.title);
                      }}
                      className="p-1 rounded text-text-tertiary hover:text-text-secondary hover:bg-krait-surface3 transition-colors"
                      title="Rename"
                    >
                      <Pencil className="w-3 h-3" strokeWidth={1.5} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTogglePin(conv.id, conv.is_pinned);
                      }}
                      className={cn(
                        'p-1 rounded transition-colors',
                        conv.is_pinned ? 'text-venom-yellow' : 'text-text-tertiary hover:text-text-secondary hover:bg-krait-surface3'
                      )}
                      title={conv.is_pinned ? 'Unpin' : 'Pin'}
                    >
                      {conv.is_pinned ? (
                        <PinOff className="w-3 h-3" strokeWidth={1.5} />
                      ) : (
                        <Pin className="w-3 h-3" strokeWidth={1.5} />
                      )}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(conv.id);
                      }}
                      className="p-1 rounded text-text-tertiary hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-3 h-3" strokeWidth={1.5} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
