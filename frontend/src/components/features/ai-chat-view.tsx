'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter, usePathname } from 'next/navigation';
import { ChevronDown, Pin, PinOff, Pencil, Loader2 } from 'lucide-react';
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
import type { ErrorDetails } from '@/types/domain/ai';
import { MessageRole, MessageStatus } from '@/types/domain/ai';

interface StreamChunk {
  content?: string;
  done?: boolean;
  conversation_id?: string;
  title?: string;
  [key: string]: unknown;
}

interface AiChatViewProps {
  workspaceSlug: string;
  initialConversationId?: string;
}

export function AiChatView({ workspaceSlug, initialConversationId }: AiChatViewProps) {
  const router = useRouter();
  const pathname = usePathname();
  const workspaceId = useAuthStore(s => s.workspaceId);
  const storeSetActiveConversation = useAiConversationStore(s => s.setActiveConversation);
  const storeSetConversationTitle = useAiConversationStore(s => s.setConversationTitle);
  const storeSetPinned = useAiConversationStore(s => s.setPinned);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [rateLimited, setRateLimited] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState('krait-2.0');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversationTitle, setConversationTitle] = useState('');
  const [isPinned, setIsPinned] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [initialLoading, setInitialLoading] = useState(!!initialConversationId);
  const abortRef = useRef<AbortController | null>(null);
  useDetailBreadcrumb(conversationId ? conversationTitle || 'Untitled' : null);
  const listRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
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

  const modelsQuery = useQuery({
    queryKey: ['ai-models'],
    queryFn: () => aiApi.listModels(),
    staleTime: 300_000,
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
    setShouldAutoScroll(nearBottom);
  }, []);

  useEffect(() => {
    if (shouldAutoScroll) scrollToBottom(isStreaming);
  }, [messages, isStreaming, scrollToBottom, shouldAutoScroll]);

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

  /* ─── Load initial conversation from URL ──────────────── */

  useEffect(() => {
    if (initialConversationId) {
      loadConversation(initialConversationId).finally(() => setInitialLoading(false));
    } else {
      setInitialLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ─── Sync conversationId to URL ─────────────────────── */

  useEffect(() => {
    if (!conversationId) return;
    const expectedPath = `/${workspaceSlug}/ai/${conversationId}`;
    if (pathname !== expectedPath) {
      router.replace(expectedPath);
    }
  }, [conversationId, workspaceSlug, router, pathname]);

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
      setThinkingStatus('Thinking');
      setShouldAutoScroll(true);
      if (!conversationId) {
        const tempTitle = trimmed.length > 60 ? trimmed.slice(0, 60) + '...' : trimmed;
        setConversationTitle(tempTitle);
        storeSetConversationTitle(tempTitle);
      }

      try {
        let accumulated = '';
        let newConvId = conversationId;
        let hasError = false;
        const controller = new AbortController();
        abortRef.current = controller;
        const stream = aiApi.streamMessage({
          content: trimmed,
          context: {},
          model: selectedModel,
          sessionId: newConvId ?? undefined,
          repo_ids: repoIds,
        }, controller.signal);

        let rafPending = false;
        const flushUpdate = () => {
          rafPending = false;
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.id === assistantMsg.id) {
              next[next.length - 1] = { ...last, content: accumulated };
            }
            return next;
          });
        };

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
          // Handle structured error events from the SSE stream
          if (c.type === 'error' || ('error' in c && typeof c.error === 'string')) {
            hasError = true;
            const errorChunk = c as { type?: string; error: string; category?: string;
              suggested_action?: string; retry_after?: number | null };
            setMessages(prev => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.id === assistantMsg.id) {
                next[next.length - 1] = {
                  ...last,
                  content: errorChunk.error || 'An unexpected error occurred.',
                  status: MessageStatus.ERROR,
                  errorDetails: {
                    category: errorChunk.category || 'unknown',
                    suggested_action: errorChunk.suggested_action as ErrorDetails['suggested_action'],
                    retry_after: errorChunk.retry_after,
                  },
                };
              }
              return next;
            });
            break;
          }
          if ('status' in c && typeof (c as { status?: string }).status === 'string') {
            setThinkingStatus((c as { status: string }).status);
            continue;
          }
          const text = typeof c.content === 'string' ? c.content : typeof c === 'string' ? c : '';
          if (text) accumulated += text;

          if (!rafPending) {
            rafPending = true;
            requestAnimationFrame(flushUpdate);
          }
        }

        // Only mark as SENT if no error occurred during streaming
        if (!hasError) {
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.id === assistantMsg.id) {
              next[next.length - 1] = { ...last, status: MessageStatus.SENT };
            }
            return next;
          });
        }
      } catch (err) {
        const isAbort = err instanceof DOMException && err.name === 'AbortError';
        const isAiError = err instanceof AiApiError;
        const isRateLimit = isAiError && err.status === 429;
        if (isRateLimit) setRateLimited(true);
        if (!isAbort) {
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.id === assistantMsg.id) {
              const errorDetails = isAiError ? {
                category: err.code || 'unknown',
                suggested_action: err.suggestedAction,
                retry_after: err.retryAfter,
              } : undefined;
              next[next.length - 1] = {
                ...last,
                content: isAiError
                  ? err.message
                  : last.content || 'Sorry, something went wrong. Please try again.',
                status: MessageStatus.ERROR,
                errorDetails,
              };
            }
            return next;
          });
        }
      } finally {
        setIsStreaming(false);
        setThinkingStatus('');
        // Safety net: ensure assistant message is never left in SENDING state
        setMessages(prev => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.id === assistantMsg.id && last.status === MessageStatus.SENDING) {
            next[next.length - 1] = {
              ...last,
              content: last.content || 'Something went wrong. Please try again.',
              status: MessageStatus.ERROR,
            };
          }
          return next;
        });
      }
    },
    [input, isStreaming, conversationId, selectedModel, storeSetConversationTitle]
  );

  /* ─── Stop streaming ────────────────────────────────── */

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

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

  if (initialLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-krait-void">
        <Loader2 className="w-5 h-5 text-venom-yellow animate-spin" />
      </div>
    );
  }

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
          models={modelsQuery.data}
          onStop={handleStop}
        />
      ) : (
        <>
          {/* Message list */}
          <div
            ref={listRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto overflow-x-hidden scroll-smooth"
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
                    thinkingStatus={isStreamingMsg ? thinkingStatus : undefined}
                    onRegenerate={isAssistant && msg.status === MessageStatus.ERROR ? handleRegenerate : undefined}
                    onEdit={msg.role === MessageRole.USER ? handleEditMessage : undefined}
                    onAddKey={isAssistant && msg.status === MessageStatus.ERROR ? () => {
                      // Trigger BYOK dialog — dispatch custom event
                      window.dispatchEvent(new CustomEvent('ai-open-byok'));
                    } : undefined}
                    onSwitchModel={isAssistant && msg.status === MessageStatus.ERROR ? () => {
                      // Trigger model selector — dispatch custom event
                      window.dispatchEvent(new CustomEvent('ai-open-model-selector'));
                    } : undefined}
                  />
                );
              })}
            </div>

            <UpgradeCard show={rateLimited} />

            <div ref={bottomRef} />
          </div>

          {/* Scroll to bottom arrow */}
          {!shouldAutoScroll && messages.length > 0 && (
            <div className="absolute bottom-[160px] left-1/2 -translate-x-1/2 z-10">
              <button
                onClick={() => {
                  scrollToBottom();
                  setShouldAutoScroll(true);
                }}
                className="w-6 h-6 rounded-full border border-krait-border bg-black/10 backdrop-blur-sm flex items-center justify-center text-text-tertiary hover:bg-white/10 transition-colors"
                aria-label="Scroll to latest message"
              >
                <ChevronDown className="w-3 h-3" strokeWidth={3} />
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
                models={modelsQuery.data}
                onStop={handleStop}
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
