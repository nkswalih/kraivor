'use client';

import { useState } from 'react';
import { MessagesSquare, Shield, FileText, Gauge, CheckCircle, BotMessageSquare, Pin, PinOff, Pencil, Check, X } from 'lucide-react';
import { AiInput } from '@/components/features/ai-input';
import { aiApi } from '@/lib/api/ai-api';
import type { ConversationSummary, ModelItem } from '@/lib/api/ai-api';
import type { DailyUsage, ChatMode } from '@/types/domain/ai';

interface AiWelcomeProps {
  workspaceAvatar?: string | null;
  conversations: ConversationSummary[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onSuggestion: (text: string) => void;
  onLoadConversation: (id: string) => void;
  onRefreshConversations?: () => void;
  isStreaming: boolean;
  selectedModel: string;
  onModelSelect: (id: string) => void;
  showBanner: boolean;
  models?: ModelItem[];
  onStop?: () => void;
  dailyUsage?: DailyUsage;
  chatMode?: ChatMode;
  onModeChange?: (mode: ChatMode) => void;
}

const SUGGESTIONS = [
  { id: 's1', icon: Shield, text: 'Analyze repository security vulnerabilities' },
  { id: 's2', icon: FileText, text: 'Generate full architecture blueprint (.md)' },
  { id: 's3', icon: Gauge, text: 'Audit component rendering performance' },
  { id: 's4', icon: CheckCircle, text: 'Review code style consistency' },
];

export function AiWelcome({
  workspaceAvatar,
  conversations,
  input,
  onInputChange,
  onSend,
  onKeyDown,
  onSuggestion,
  onLoadConversation,
  onRefreshConversations,
  isStreaming,
  selectedModel,
  onModelSelect,
  showBanner,
  models,
  onStop,
  dailyUsage,
  chatMode,
  onModeChange,
}: AiWelcomeProps) {
  const [editingConv, setEditingConv] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  const sorted = [...conversations].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return 0;
  });

  const handleRename = async (convId: string, newTitle: string) => {
    const trimmed = newTitle.trim();
    if (trimmed && trimmed !== conversations.find(c => c.id === convId)?.title) {
      await aiApi.updateConversation(convId, { title: trimmed });
      onRefreshConversations?.();
    }
    setEditingConv(null);
  };

  const handleTogglePin = async (convId: string, currentlyPinned: boolean) => {
    await aiApi.updateConversation(convId, { is_pinned: !currentlyPinned });
    onRefreshConversations?.();
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[720px] mx-auto px-6 pt-16 pb-8">
        {/* Header */}
        <div className="text-center mb-8 animate-fade-up">
          {workspaceAvatar ? (
            <img
              src={workspaceAvatar}
              alt=""
              className="w-14 h-14 rounded-full object-cover mx-auto mb-5 bg-krait-surface2"
            />
          ) : (
            <div className="w-14 h-14 rounded-2xl bg-krait-surface3 border border-krait-border flex items-center justify-center mx-auto mb-5">
              <BotMessageSquare className="w-7 h-7 text-venom-yellow" />
            </div>
          )}
          <h1 className="text-[22px] font-bold text-text-primary tracking-tight">
            How can I help you today?
          </h1>
        </div>

        {/* Input */}
        <div className="animate-fade-up" style={{ animationDelay: '0.1s' }}>
          <AiInput
            value={input}
            onChange={onInputChange}
            onSend={onSend}
            onKeyDown={onKeyDown}
            isStreaming={isStreaming}
            selectedModel={selectedModel}
            onModelSelect={onModelSelect}
            showBanner={showBanner}
            models={models}
            onStop={onStop}
            dailyUsage={dailyUsage}
            chatMode={chatMode}
            onModeChange={onModeChange}
          />
        </div>

        {/* Suggestions grid */}
        <div className="grid grid-cols-2 gap-8 mt-12 animate-fade-up" style={{ animationDelay: '0.2s' }}>
          <div>
            <div className="text-[10px] uppercase tracking-[0.12em] font-medium text-text-tertiary mb-3">
              RECENT CHATS
            </div>
            <div className="space-y-0.5">
              {sorted.length === 0 && (
                <p className="text-[13px] text-text-tertiary px-3 py-2">
                  No conversations yet
                </p>
              )}
              {sorted.map(conv => (
                <div
                  key={conv.id}
                  className="group flex items-center gap-1 px-1 rounded-md hover:bg-krait-surface3 transition-colors"
                >
                  {editingConv === conv.id ? (
                    <div className="flex items-center gap-1 flex-1 min-w-0 py-2">
                      <input
                        type="text"
                        value={editValue}
                        onChange={e => setEditValue(e.target.value)}
                        className="flex-1 bg-transparent border-b border-venom-yellow/50 text-[13px] text-text-primary outline-none min-w-0"
                        autoFocus
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleRename(conv.id, editValue);
                          if (e.key === 'Escape') setEditingConv(null);
                        }}
                      />
                      <button
                        onClick={() => handleRename(conv.id, editValue)}
                        className="p-1 rounded text-text-secondary hover:text-text-primary"
                      >
                        <Check className="w-3.5 h-3.5" strokeWidth={1.5} />
                      </button>
                      <button
                        onClick={() => setEditingConv(null)}
                        className="p-1 rounded text-text-tertiary hover:text-text-secondary"
                      >
                        <X className="w-3.5 h-3.5" strokeWidth={1.5} />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => onLoadConversation(conv.id)}
                      className="flex items-center gap-3 px-2 py-2 flex-1 min-w-0 text-left"
                    >
                      <MessagesSquare
                        className="w-4 h-4 text-text-tertiary shrink-0"
                        strokeWidth={1.5}
                      />
                      <span className="text-[13px] text-text-secondary truncate">
                        {conv.title}
                      </span>
                    </button>
                  )}

                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    {editingConv !== conv.id && (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingConv(conv.id);
                            setEditValue(conv.title);
                          }}
                          className="p-1 rounded text-text-tertiary hover:text-text-secondary"
                          title="Rename"
                        >
                          <Pencil className="w-3 h-3" strokeWidth={1.5} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTogglePin(conv.id, conv.is_pinned);
                          }}
                          className={`p-1 rounded transition-colors ${
                            conv.is_pinned ? 'text-venom-yellow' : 'text-text-tertiary hover:text-text-secondary'
                          }`}
                          title={conv.is_pinned ? 'Unpin' : 'Pin'}
                        >
                          {conv.is_pinned ? (
                            <PinOff className="w-3 h-3" strokeWidth={1.5} />
                          ) : (
                            <Pin className="w-3 h-3" strokeWidth={1.5} />
                          )}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase tracking-[0.12em] font-medium text-text-tertiary mb-3">
              SUGGESTED ANALYSIS
            </div>
            <div className="space-y-0.5">
              {SUGGESTIONS.map(s => {
                const Icon = s.icon;
                return (
                  <button
                    key={s.id}
                    onClick={() => onSuggestion(s.text)}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-krait-surface3 transition-colors text-left group"
                  >
                    <Icon
                      className="w-4 h-4 text-text-tertiary shrink-0 group-hover:text-text-secondary transition-colors"
                      strokeWidth={1.5}
                    />
                    <span className="text-[13px] text-text-secondary group-hover:text-text-primary transition-colors">
                      {s.text}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
