'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Pin, PinOff, Pencil } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useAiConversationStore } from '@/lib/stores/ai-conversation-store';
import { workspaceEndpoints, repositoryEndpoints } from '@/lib/api/endpoints';
import { aiApi, AiApiError } from '@/lib/api/ai-api';
import type { HistoryMessage } from '@/lib/api/ai-api';
import { AiInput } from '@/components/features/ai-input';
import { AiMessage } from '@/components/features/ai-message';
import { useDetailBreadcrumb } from '@/lib/hooks/use-detail-breadcrumb';
import { AiWelcome } from '@/components/features/ai-welcome';
import { UpgradeCard } from '@/components/features/upgrade-card';
import type { ChatMessage } from '@/types/domain/ai';
import { MessageRole, MessageStatus } from '@/types/domain/ai';

interface StreamChunk {
  content?: string;
  done?: boolean;
  conversation_id?: string;
  title?: string;
  [key: string]: unknown;
}

export function AiChatView({ workspaceSlug }: { workspaceSlug: string }) {
  const workspaceId = useAuthStore(s => s.workspaceId);
  const storeSetActiveConversation = useAiConversationStore(s => s.setActiveConversation);
  const storeSetConversationTitle = useAiConversationStore(s => s.setConversationTitle);
  const storeSetPinned = useAiConversationStore(s => s.setPinned);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [rateLimited, setRateLimited] = useState(false);
  const [selectedModel, setSelectedModel] = useState('krait-2.0');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversationTitle, setConversationTitle] = useState('');
  const [isPinned, setIsPinned] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  useDetailBreadcrumb(conversationId ? conversationTitle || 'Untitled' : null);
  const listRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);
  const titleInputRef = useRef<HTMLInputElement>(null);

  const { data: workspace } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceEndpoints.get(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });

  const { data: reposData } = useQuery({
    queryKey: ['repositories', workspaceId],
    queryFn: () => repositoryEndpoints.list(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });

  const repoIds = reposData?.map(r => r.id) ?? [];

  const convListQuery = useQuery({
    queryKey: ['ai-conversations', workspaceId],
    queryFn: () => aiApi.listConversations(workspaceId ?? undefined),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });

  const conversations = convListQuery.data?.conversations ?? [];
  const workspaceAvatar = workspace?.avatar_url;

  /* ─── Scroll management ───────────────────────────────── */

  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  }, []);

  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    shouldAutoScroll.current = nearBottom;
  }, []);

  useEffect(() => {
    if (shouldAutoScroll.current) scrollToBottom(isStreaming);
  }, [messages, isStreaming, scrollToBottom]);

  /* ─── Load previous conversation ──────────────────────── */

  const loadConversation = useCallback(async (convId: string) => {
    setConversationId(convId);
    setEditingTitle(false);
    try {
      const [res, convData] = await Promise.all([
        aiApi.getMessages(convId),
        aiApi.listConversations(workspaceId ?? undefined),
      ]);
      const loaded: ChatMessage[] = res.messages.map((m: HistoryMessage) => ({
        id: m.id,
        role: m.role as MessageRole,
        content: m.content,
        timestamp: m.created_at,
        status: MessageStatus.SENT,
      }));
      setMessages(loaded);
      const match = convData.conversations.find(c => c.id === convId);
      if (match) {
        setConversationTitle(match.title);
        setIsPinned(match.is_pinned);
        storeSetActiveConversation(convId, match.title, match.is_pinned);
      }
    } catch {
      setMessages([]);
    }
  }, [storeSetActiveConversation]);

  /* ─── Regenerate last response ────────────────────────── */

  const handleRegenerate = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find(m => m.role === MessageRole.USER);
    if (!lastUserMsg) return;
    handleSend(lastUserMsg.content);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  /* ─── Send message (also used for regeneration) ───────── */

  const handleSend = useCallback(
    async (overrideContent?: string) => {
      const trimmed = (overrideContent ?? input).trim();
      if (!trimmed || isStreaming) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: MessageRole.USER,
        content: trimmed,
        timestamp: new Date().toISOString(),
        status: MessageStatus.SENT,
      };

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: MessageRole.ASSISTANT,
        content: '',
        timestamp: new Date().toISOString(),
        status: MessageStatus.SENDING,
      };

      setMessages(prev => [...prev, userMsg, assistantMsg]);
      setInput('');
      setIsStreaming(true);
      shouldAutoScroll.current = true;
      if (!conversationId) {
        const tempTitle = trimmed.length > 60 ? trimmed.slice(0, 60) + '...' : trimmed;
        setConversationTitle(tempTitle);
        storeSetConversationTitle(tempTitle);
      }

      try {
        let accumulated = '';
        let newConvId = conversationId;
        const stream = aiApi.streamMessage({
          content: trimmed,
          context: {},
          model: selectedModel,
          sessionId: newConvId ?? undefined,
          repo_ids: repoIds,
        });

        for await (const chunk of stream) {
          const c = chunk as StreamChunk;
          if (c.done) {
            if (c.conversation_id && !newConvId) {
              newConvId = c.conversation_id;
              setConversationId(c.conversation_id);
            }
            if (c.title && typeof c.title === 'string') {
              setConversationTitle(c.title);
              storeSetConversationTitle(c.title);
            }
            break;
          }
          const text = typeof c.content === 'string' ? c.content : typeof c === 'string' ? c : '';
          if (text) accumulated += text;

          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.id === assistantMsg.id) {
              next[next.length - 1] = { ...last, content: accumulated };
            }
            return next;
          });
        }

        setMessages(prev => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.id === assistantMsg.id) {
            next[next.length - 1] = { ...last, status: MessageStatus.SENT };
          }
          return next;
        });
      } catch (err) {
        const isRateLimit = err instanceof AiApiError && err.status === 429;
        if (isRateLimit) setRateLimited(true);
        setMessages(prev => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.id === assistantMsg.id) {
            next[next.length - 1] = {
              ...last,
              content: isRateLimit
                ? "You've hit the rate limit. Upgrade to Kraivor Pro for higher limits."
                : last.content || 'Sorry, something went wrong.',
              status: MessageStatus.ERROR,
            };
          }
          return next;
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [input, isStreaming, conversationId, selectedModel, storeSetConversationTitle]
  );

  /* ─── Edit user message ──────────────────────────────── */

  const handleEditMessage = useCallback((content: string) => {
    setInput(content);
    // Remove the user + assistant messages from the list so user can resend
    setMessages(prev => {
      const idx = [...prev].reverse().findIndex(m => m.role === MessageRole.USER);
      if (idx === -1) return prev;
      const userIdx = prev.length - 1 - idx;
      // Remove user message and any following assistant message
      const endIdx = userIdx + 1 < prev.length && prev[userIdx + 1].role === MessageRole.ASSISTANT
        ? userIdx + 2
        : userIdx + 1;
      return prev.slice(0, userIdx).concat(prev.slice(endIdx));
    });
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent, overrideContent?: string) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(overrideContent);
    }
  };

  /* ─── Render ──────────────────────────────────────────── */

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full bg-krait-void relative">
      {isEmpty ? (
        <AiWelcome
          workspaceAvatar={workspaceAvatar}
          conversations={conversations}
          input={input}
          onInputChange={setInput}
          onSend={() => handleSend()}
          onKeyDown={e => handleKeyDown(e)}
          onSuggestion={text => handleSend(text)}
          onLoadConversation={loadConversation}
          onRefreshConversations={() => { convListQuery.refetch() }}
          isStreaming={isStreaming}
          selectedModel={selectedModel}
          onModelSelect={setSelectedModel}
          showBanner={false}
        />
      ) : (
        <>
          {/* Message list */}
          <div
            ref={listRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto scroll-smooth"
          >
            {/* Chat header — editable title + pin */}
            <div className="px-4 pt-4 pb-1">
              <div className="max-w-[720px] mx-auto flex items-center gap-2">
                {editingTitle ? (
                  <input
                    ref={titleInputRef}
                    type="text"
                    defaultValue={conversationTitle}
                    className="flex-1 bg-transparent border-b border-venom-yellow/50 text-[15px] font-semibold text-text-primary outline-none py-0.5"
                    onBlur={async (e) => {
                      const val = e.target.value.trim();
                      if (val && conversationId) {
                        await aiApi.updateConversation(conversationId, { title: val });
                        setConversationTitle(val);
                        storeSetConversationTitle(val);
                      }
                      setEditingTitle(false);
                    }}
                    onKeyDown={async (e) => {
                      if (e.key === 'Enter') {
                        (e.target as HTMLInputElement).blur();
                      }
                      if (e.key === 'Escape') {
                        setEditingTitle(false);
                      }
                    }}
                    autoFocus
                  />
                ) : (
                  <button
                    onClick={() => setEditingTitle(true)}
                    className="flex-1 flex items-center gap-2 text-left group/title min-w-0"
                  >
                    <span className="text-[15px] font-semibold text-text-primary truncate">
                      {conversationTitle}
                    </span>
                    <Pencil className="w-3.5 h-3.5 text-text-tertiary opacity-0 group-hover/title:opacity-100 transition-opacity shrink-0" strokeWidth={1.5} />
                  </button>
                )}

                {conversationId && (
                  <button
                    onClick={async () => {
                      const next = !isPinned;
                      await aiApi.updateConversation(conversationId, { is_pinned: next });
                      setIsPinned(next);
                      storeSetPinned(next);
                    }}
                    className="p-1.5 rounded-md text-text-tertiary hover:text-venom-yellow hover:bg-krait-surface3 transition-all"
                    title={isPinned ? 'Unpin' : 'Pin'}
                  >
                    {isPinned ? (
                      <PinOff className="w-3.5 h-3.5" strokeWidth={1.5} />
                    ) : (
                      <Pin className="w-3.5 h-3.5" strokeWidth={1.5} />
                    )}
                  </button>
                )}
              </div>
            </div>

            <div className="py-4 pb-6">
              {messages.map((msg) => {
                const isAssistant = msg.role === MessageRole.ASSISTANT;
                const isStreamingMsg = isAssistant && msg.status === MessageStatus.SENDING;

                return (
                  <AiMessage
                    key={msg.id}
                    message={msg}
                    isStreaming={isStreamingMsg}
                    onRegenerate={isAssistant && msg.status === MessageStatus.ERROR ? handleRegenerate : undefined}
                    onEdit={msg.role === MessageRole.USER ? handleEditMessage : undefined}
                  />
                );
              })}
            </div>

            <UpgradeCard show={rateLimited} />

            <div ref={bottomRef} />
          </div>

          {/* New messages button */}
          {!shouldAutoScroll.current && messages.length > 0 && (
            <div className="flex justify-center py-3">
              <button
                onClick={() => {
                  scrollToBottom();
                  shouldAutoScroll.current = true;
                }}
                className="bg-krait-surface3 border border-krait-border rounded-full px-3 py-1.5 text-[12px] text-text-secondary hover:text-text-primary hover:bg-krait-surface4 shadow-lg flex items-center gap-1.5 transition-colors"
              >
                <ChevronDown className="w-3.5 h-3.5" /> New messages
              </button>
            </div>
          )}

          {/* Input area — continuous with conversation */}
          <div className="shrink-0 pb-3 pt-1">
            <div className="px-4">
              <AiInput
                value={input}
                onChange={setInput}
                onSend={() => handleSend()}
                onKeyDown={e => handleKeyDown(e)}
                isStreaming={isStreaming}
                selectedModel={selectedModel}
                onModelSelect={setSelectedModel}
                showBanner={rateLimited}
              />
            </div>
            <p className="text-center text-[11px] text-text-tertiary mt-2.5 px-4">
              AI can make mistakes. Verify critical code architectures.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
