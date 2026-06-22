'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Sparkles,
  ChevronDown,
  MessageSquare,
  Shield,
  FileText,
  Gauge,
  CheckCircle,
} from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { workspaceEndpoints } from '@/lib/api/endpoints';
import { aiApi } from '@/lib/api/ai-api';
import { AiInput } from '@/components/features/ai-input';
import { UpgradeCard } from '@/components/features/upgrade-card';
import type { ChatMessage } from '@/types/domain/ai';
import { MessageRole, MessageStatus } from '@/types/domain/ai';

interface StreamChunk {
  content?: string;
  done?: boolean;
  [key: string]: unknown;
}

const RECENT_CHATS = [
  { id: '1', title: 'auth-service codebase check' },
  { id: '2', title: 'API security audit results' },
  { id: '3', title: 'This is a brilliant pivot. You are movin...' },
];

const SUGGESTIONS = [
  { id: 's1', icon: Shield, text: 'Analyze repository security vulnerabilities' },
  { id: 's2', icon: FileText, text: 'Generate full architecture blueprint (.md)' },
  { id: 's3', icon: Gauge, text: 'Audit component rendering performance' },
  { id: 's4', icon: CheckCircle, text: 'Review code style consistency' },
];

export function AiChatView({ workspaceSlug }: { workspaceSlug: string }) {
  const workspaceId = useAuthStore(s => s.workspaceId);

  /* ─── Messages state ────────────────────────────────────────── */
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedModel, setSelectedModel] = useState('sonnet-4.6');
  const listRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);

  /* ─── Fetch workspace plan for upgrade gating ──────────────── */
  const { data: workspace } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceEndpoints.get(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });

  const isFreePlan = workspace?.plan === 'free';
  const workspaceAvatar = workspace?.avatar_url;

  /* ─── Scroll helpers ───────────────────────────────────────── */
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

  /* ─── Send message ─────────────────────────────────────────── */
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

      try {
        let accumulated = '';
        const stream = aiApi.streamMessage({
          content: trimmed,
          context: {},
        });

        for await (const chunk of stream) {
          const c = chunk as StreamChunk;
          if (c.done) break;
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
      } catch {
        setMessages(prev => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.id === assistantMsg.id) {
            next[next.length - 1] = {
              ...last,
              content: last.content || 'Sorry, something went wrong.',
              status: MessageStatus.ERROR,
            };
          }
          return next;
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [input, isStreaming]
  );

  const handleKeyDown = (e: React.KeyboardEvent, overrideContent?: string) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(overrideContent);
    }
  };

  /* ─── Render ───────────────────────────────────────────────── */
  return (
    <div className="flex flex-col h-full bg-[#0A0A0B] relative">
      {messages.length === 0 ? (
        /* ── Empty State: Hero + Input + Grid ──────────────────── */
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-[720px] mx-auto px-6 pt-16 pb-8">
            {/* Hero */}
            <div className="text-center mb-8">
              {workspaceAvatar ? (
                <img
                  src={workspaceAvatar}
                  alt=""
                  className="w-14 h-14 rounded-full object-cover mx-auto mb-5 bg-[#1C1C1F]"
                />
              ) : (
                <div className="w-14 h-14 rounded-2xl bg-[#1C1C1F] border border-[#27272A] flex items-center justify-center mx-auto mb-5">
                  <Sparkles className="w-7 h-7 text-venom-yellow" />
                </div>
              )}
              <h1 className="text-[22px] font-bold text-[#f2f2f3] tracking-tight">
                How can I help you today?
              </h1>
            </div>

            {/* Input */}
            <AiInput
              value={input}
              onChange={setInput}
              onSend={() => handleSend()}
              onKeyDown={e => handleKeyDown(e)}
              isStreaming={isStreaming}
              selectedModel={selectedModel}
              onModelSelect={setSelectedModel}
              showBanner={false}
            />

            {/* Two-column grid */}
            <div className="grid grid-cols-2 gap-8 mt-12">
              {/* Left: Recent Chats */}
              <div>
                <div className="text-[10px] uppercase tracking-[0.12em] font-medium text-[#5e5e72] mb-3">
                  RECENT CHATS
                </div>
                <div className="space-y-0.5">
                  {RECENT_CHATS.map(chat => (
                    <button
                      key={chat.id}
                      onClick={() => handleSend(chat.title)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#1C1C1F] transition-colors text-left group"
                    >
                      <MessageSquare
                        className="w-4 h-4 text-[#5e5e72] shrink-0 group-hover:text-[#9898a6] transition-colors"
                        strokeWidth={1.5}
                      />
                      <span className="text-[13px] text-[#9898a6] truncate group-hover:text-[#d1d5db] transition-colors">
                        {chat.title}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Right: Suggested Analysis */}
              <div>
                <div className="text-[10px] uppercase tracking-[0.12em] font-medium text-[#5e5e72] mb-3">
                  SUGGESTED ANALYSIS
                </div>
                <div className="space-y-0.5">
                  {SUGGESTIONS.map(s => {
                    const Icon = s.icon;
                    return (
                      <button
                        key={s.id}
                        onClick={() => handleSend(s.text)}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[#1C1C1F] transition-colors text-left group"
                      >
                        <Icon
                          className="w-4 h-4 text-[#5e5e72] shrink-0 group-hover:text-[#9898a6] transition-colors"
                          strokeWidth={1.5}
                        />
                        <span className="text-[13px] text-[#9898a6] group-hover:text-[#d1d5db] transition-colors">
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
      ) : (
        /* ── Messages State ───────────────────────────────────── */
        <>
          {/* Messages Area */}
          <div ref={listRef} onScroll={handleScroll} className="flex-1 overflow-y-auto">
            <div className="max-w-[720px] mx-auto px-6 py-4">
              <div className="space-y-1">
                {messages.map((msg, idx) => {
                  const isUser = msg.role === MessageRole.USER;
                  const isAssistant = msg.role === MessageRole.ASSISTANT;
                  const isStreamingMsg = isAssistant && msg.status === MessageStatus.SENDING;
                  const prev = idx > 0 ? messages[idx - 1] : undefined;
                  const isNewGroup = !prev || prev.role !== msg.role;

                  return (
                    <div key={msg.id} className="py-2">
                      {isNewGroup && (
                        <div className="flex items-center gap-2 mb-2 mt-3 first:mt-0">
                          <div
                            className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                              isUser
                                ? 'bg-[#27272A]'
                                : 'bg-venom-yellow/10 border border-venom-yellow/20'
                            }`}
                          >
                            {isUser ? (
                              <span className="text-[11px] font-bold text-[#9898a6]">ME</span>
                            ) : (
                              <Sparkles className="w-3.5 h-3.5 text-venom-yellow" />
                            )}
                          </div>
                          <span className="text-[13px] font-semibold text-[#f2f2f3]">
                            {isUser ? 'You' : 'Kraivor AI'}
                          </span>
                          {!isStreamingMsg && msg.timestamp && (
                            <span className="text-[11px] text-[#5e5e72]">
                              {new Date(msg.timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          )}
                        </div>
                      )}

                      <div className={`ml-9 ${isUser ? 'pr-0' : ''}`}>
                        {isStreamingMsg ? (
                          <div className="flex items-center gap-2 text-[14px] text-[#9898a6]">
                            <span className="w-1.5 h-1.5 rounded-full bg-venom-yellow animate-pulse-venom" />
                            Thinking...
                          </div>
                        ) : isUser ? (
                          <p className="text-[14px] text-[#f2f2f3] leading-relaxed whitespace-pre-wrap break-words">
                            {msg.content}
                          </p>
                        ) : (
                          <div className="text-[14px] text-[#d1d5db] leading-relaxed whitespace-pre-wrap break-words">
                            {formatAssistantContent(msg.content)}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <UpgradeCard show={isFreePlan && messages.length > 0} />

              <div ref={bottomRef} />
            </div>

            {!shouldAutoScroll.current && messages.length > 0 && (
              <div className="sticky bottom-2 flex justify-center">
                <button
                  onClick={() => {
                    scrollToBottom();
                    shouldAutoScroll.current = true;
                  }}
                  className="bg-[#27272A] border border-[#3A3A3D] rounded-full px-3 py-1.5 text-[12px] text-[#f2f2f3] hover:bg-[#3A3A3D] shadow-lg flex items-center gap-1.5 transition-colors"
                >
                  <ChevronDown className="w-3.5 h-3.5" /> New messages
                </button>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="px-4 pb-4 pt-3 shrink-0 border-t border-[#27272A] bg-[#0A0A0B]">
            <AiInput
              value={input}
              onChange={setInput}
              onSend={() => handleSend()}
              onKeyDown={e => handleKeyDown(e)}
              isStreaming={isStreaming}
              selectedModel={selectedModel}
              onModelSelect={setSelectedModel}
              showBanner={isFreePlan}
            />
            <p className="text-center text-[11px] text-[#5e5e72] mt-1.5">
              AI can make mistakes. Verify critical code architectures.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Helper: render assistant content with code block formatting ─── */
function formatAssistantContent(content: string) {
  const parts = content.split(/(```[\s\S]*?```)/g);
  if (parts.length === 1) {
    return applyInlineCode(content);
  }
  return parts.map((part, i) => {
    if (part.startsWith('```') && part.endsWith('```')) {
      const code = part.slice(3, -3);
      const langEnd = code.indexOf('\n');
      const lang = langEnd > 0 ? code.slice(0, langEnd).trim() : '';
      const body = langEnd > 0 ? code.slice(langEnd + 1) : code;
      return (
        <div key={i} className="my-2 border-l-2 border-venom-yellow/30 pl-4 py-1">
          {lang && (
            <div className="text-[11px] text-[#5e5e72] font-mono uppercase tracking-wider mb-1">
              {lang}
            </div>
          )}
          <pre className="text-[13px] text-[#d1d5db] font-mono leading-relaxed whitespace-pre-wrap overflow-x-auto">
            {body}
          </pre>
        </div>
      );
    }
    return <span key={i}>{applyInlineCode(part)}</span>;
  });
}

function applyInlineCode(text: string) {
  const parts = text.split(/(`[^`]+`)/g);
  if (parts.length === 1) return text;
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={i}
          className="bg-[#1C1C1F] border border-[#27272A] px-1.5 py-0.5 rounded text-[13px] text-venom-yellow/90 font-mono"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}
