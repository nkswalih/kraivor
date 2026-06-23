'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Hash, Send, Loader2, ChevronDown, Trash2, Edit3, X, Check } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useChatStore } from '@/lib/stores/chat-store';
import { chatEndpoints, profileEndpoints } from '@/lib/api/endpoints';
import { ChatSocket } from '@/lib/ws/chat-socket';
import { ChannelSidebar } from '@/components/features/channel-sidebar';
import { MembersPanel } from '@/components/features/members-panel';
import { formatRelativeTime } from '@/lib/utils';
import { avatarUrl } from '@/lib/utils';
import {
  SkeletonMessage,
  SkeletonChatSidebar,
  SkeletonBlock,
  SkeletonLine,
} from '@/components/ui/skeletons';
import type { ChatMessage } from '@/types/api';

export default function ChatRoomPage() {
  const params = useParams<{ roomId: string; workspace: string }>();
  const roomId = params?.roomId ?? '';
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);
  const queryClient = useQueryClient();
  const userId = useAuthStore(s => s.user?.id);

  const {
    messagesByRoom,
    addMessage,
    prependMessages,
    setNextKey,
    nextKeyByRoom,
    removeMessage,
    updateMessage,
    setCurrentRoom,
  } = useChatStore();
  const messages = messagesByRoom[roomId] ?? [];
  const nextKey = nextKeyByRoom[roomId] ?? null;

  /* ─── Mark room as read on mount ──────────────────────────── */
  useEffect(() => {
    setCurrentRoom(roomId);
    return () => setCurrentRoom(null);
  }, [roomId, setCurrentRoom]);

  /* ─── Profile fetch for sender avatars ────────────────────── */
  const senderIds = useMemo(() => {
    const ids = new Set<string>();
    for (const m of messages) if (m.sender_id) ids.add(m.sender_id);
    return Array.from(ids);
  }, [messages]);

  const { data: senderProfiles } = useQuery({
    queryKey: ['profiles-by-ids', senderIds],
    queryFn: () => profileEndpoints.getProfilesByIds(senderIds),
    enabled: senderIds.length > 0,
    staleTime: 60_000,
  });

  const senderProfileMap: Record<string, { avatar_url?: string; user_avatar_url?: string }> =
    useMemo(() => senderProfiles?.profiles ?? {}, [senderProfiles]);

  const [input, setInput] = useState('');
  const [loadingMore, setLoadingMore] = useState(false);
  const [editingMsg, setEditingMsg] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [onlineUserIds, setOnlineUserIds] = useState<Set<string>>(new Set());
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const socketRef = useRef<ChatSocket | null>(null);
  const shouldAutoScroll = useRef(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  /* ─── Room detail ─────────────────────────────────────────── */
  const { data: room } = useQuery({
    queryKey: ['room', workspaceId, roomId],
    queryFn: () => chatEndpoints.getRoom(workspaceId!, roomId),
    enabled: !!workspaceId && !!roomId,
  });

  /* ─── Messages fetch ──────────────────────────────────────── */
  const { isLoading: msgsLoading } = useQuery({
    queryKey: ['messages', workspaceId, roomId],
    queryFn: async () => {
      const page = await chatEndpoints.listMessages(workspaceId!, roomId, 50);
      prependMessages(roomId, page.results);
      setNextKey(roomId, page.next_start_key ?? null);
      return page;
    },
    enabled: !!workspaceId && !!roomId,
  });

  const loadOlder = useCallback(async () => {
    if (loadingMore || !nextKey) return;
    setLoadingMore(true);
    try {
      const page = await chatEndpoints.listMessages(workspaceId!, roomId, 50, nextKey);
      prependMessages(roomId, page.results);
      setNextKey(roomId, page.next_start_key ?? null);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, nextKey, workspaceId, roomId, prependMessages, setNextKey]);

  /* ─── Scroll handling ────────────────────────────────────── */
  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  }, []);

  useEffect(() => {
    if (!msgsLoading && shouldAutoScroll.current) {
      scrollToBottom(false);
    }
  }, [msgsLoading, messages.length, scrollToBottom]);

  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150;
    shouldAutoScroll.current = nearBottom;
    if (el.scrollTop < 80 && nextKey) loadOlder();
  }, [nextKey, loadOlder]);

  /* ─── Send message ───────────────────────────────────────── */
  const sendMutation = useMutation({
    mutationFn: (content: string) => chatEndpoints.sendMessage(workspaceId!, roomId, { content }),
    onSuccess: msg => {
      addMessage(roomId, msg);
      setInput('');
      shouldAutoScroll.current = true;
      setTimeout(() => scrollToBottom(), 50);
    },
  });

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || sendMutation.isPending) return;
    sendMutation.mutate(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* ─── Edit / Delete ───────────────────────────────────────── */
  const deleteMut = useMutation({
    mutationFn: (messageId: string) => chatEndpoints.deleteMessage(workspaceId!, roomId, messageId),
    onSuccess: (_, messageId) => removeMessage(roomId, messageId),
  });

  const editMut = useMutation({
    mutationFn: ({ messageId, content }: { messageId: string; content: string }) =>
      chatEndpoints.editMessage(workspaceId!, roomId, messageId, content),
    onSuccess: msg => {
      updateMessage(roomId, msg);
      setEditingMsg(null);
      setEditContent('');
    },
  });

  /* ─── WebSocket ──────────────────────────────────────────── */
  useEffect(() => {
    if (!roomId) return;
    const socket = new ChatSocket();
    socketRef.current = socket;
    socket.onEvent = event => {
      if (event.type === 'message' && event.message_id) {
        addMessage(roomId, event as unknown as ChatMessage);
      }
      if (event.type === 'presence') {
        setOnlineUserIds(prev => {
          const next = new Set(prev);
          if (event.status === 'online') next.add(event.user_id);
          else next.delete(event.user_id);
          return next;
        });
      }
    };
    socket.connect(roomId);
    return () => socket.disconnect();
  }, [roomId, addMessage]);

  /* ─── Render helpers ──────────────────────────────────────── */
  const isSameSender = (curr: ChatMessage, prev?: ChatMessage) =>
    prev && curr.sender_id === prev.sender_id;

  if (!workspaceId) {
    return (
      <div className="flex flex-1 min-h-0 w-full bg-background">
        <SkeletonChatSidebar />
        <div className="flex-1 flex flex-col bg-krait-void">
          <div className="h-[49px] border-b border-krait-border px-4 flex items-center gap-2">
            <SkeletonBlock className="w-5 h-5 rounded" />
            <SkeletonLine className="w-32" />
          </div>
          <div className="flex-1 p-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonMessage key={i} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0 w-full bg-background">
      <ChannelSidebar
        workspaceId={workspaceId}
        workspaceSlug={workspaceSlug}
        currentRoomId={roomId}
      />

      <div className="flex-1 flex flex-col min-w-0 bg-krait-void">
        {/* Chat Header */}
        <div className="h-[49px] border-b border-krait-border flex items-center px-4 shrink-0 bg-krait-void">
          <Hash className="w-5 h-5 text-text-tertiary mr-2 shrink-0" />
          <h2 className="font-semibold text-[15px] text-text-primary truncate">
            {room?.name ?? '...'}
          </h2>
          {room?.topic && (
            <span className="text-[13px] text-text-tertiary ml-3 pl-3 border-l border-krait-border truncate hidden lg:inline">
              {room.topic}
            </span>
          )}
        </div>

        {/* Messages Area */}
        <div ref={listRef} onScroll={handleScroll} className="flex-1 overflow-y-auto">
          {loadingMore && (
            <div className="flex justify-center py-3">
              <Loader2 className="w-4 h-4 text-venom-yellow animate-spin" />
            </div>
          )}

          {msgsLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-5 h-5 text-venom-yellow animate-spin" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-8">
              <div className="w-12 h-12 rounded-2xl bg-krait-surface3 flex items-center justify-center mb-4">
                <Hash className="w-6 h-6 text-text-tertiary" />
              </div>
              <h3 className="text-[17px] font-semibold text-text-primary mb-1">
                Welcome to #{room?.name ?? 'channel'}
              </h3>
              <p className="text-[14px] text-text-tertiary max-w-md">
                This is the start of the {room?.name ?? 'channel'} channel. Send a message to get
                the conversation going.
              </p>
            </div>
          ) : (
            <div className="py-2">
              {messages.map((msg, idx) => {
                const prev = idx > 0 ? messages[idx - 1] : undefined;
                const sameSender = isSameSender(msg, prev);
                const timeGap = prev
                  ? new Date(msg.created_at).getTime() - new Date(prev.created_at).getTime()
                  : Infinity;
                const showHeader = !sameSender || timeGap > 300000;
                const isEditing = editingMsg === msg.message_id;
                const isOwn = msg.sender_id === userId;

                return (
                  <div
                    key={msg.message_id}
                    className="group relative px-4 py-0.5 hover:bg-krait-surface1/20"
                  >
                    {/* Time separator */}
                    {timeGap > 600000 && prev && (
                      <div className="flex items-center gap-3 py-2">
                        <div className="flex-1 h-px bg-krait-border" />
                        <span className="text-[11px] text-text-tertiary shrink-0">
                          {new Date(msg.created_at).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </span>
                        <div className="flex-1 h-px bg-krait-border" />
                      </div>
                    )}

                    <div className={`flex gap-3 ${showHeader ? 'mt-3' : ''}`}>
                      {/* Avatar */}
                      {showHeader ? (
                        (() => {
                          const p = senderProfileMap[msg.sender_id];
                          const src = avatarUrl(p?.avatar_url, p?.user_avatar_url);
                          return src ? (
                            <img
                              src={src}
                              alt={msg.sender_name}
                              className="w-9 h-9 rounded-full object-cover shrink-0 mt-0.5 bg-krait-surface3"
                            />
                          ) : (
                            <div className="w-9 h-9 rounded-full bg-krait-surface3 flex items-center justify-center text-[13px] font-bold text-text-primary shrink-0 mt-0.5">
                              {msg.sender_name?.charAt(0)?.toUpperCase() ?? '?'}
                            </div>
                          );
                        })()
                      ) : (
                        <div className="w-9 shrink-0" />
                      )}

                      <div className="min-w-0 flex-1">
                        {/* Header row */}
                        {showHeader && (
                          <div className="flex items-baseline gap-2 mb-0.5">
                            <span className="font-semibold text-[15px] text-text-primary hover:underline cursor-pointer">
                              {msg.sender_name}
                            </span>
                            <span className="text-[11px] text-text-tertiary">
                              {formatRelativeTime(msg.created_at)}
                            </span>
                          </div>
                        )}

                        {/* Content */}
                        {isEditing ? (
                          <div className="flex items-center gap-2 mt-1">
                            <input
                              value={editContent}
                              onChange={e => setEditContent(e.target.value)}
                              className="flex-1 px-3 py-1.5 bg-krait-void border border-krait-border rounded text-[14px] text-text-primary focus:outline-none focus:border-venom-yellow/50"
                              autoFocus
                              onKeyDown={e => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                  e.preventDefault();
                                  if (editContent.trim()) {
                                    editMut.mutate({
                                      messageId: msg.message_id,
                                      content: editContent,
                                    });
                                  }
                                }
                                if (e.key === 'Escape') {
                                  setEditingMsg(null);
                                  setEditContent('');
                                }
                              }}
                            />
                            <button
                              onClick={() =>
                                editMut.mutate({ messageId: msg.message_id, content: editContent })
                              }
                              disabled={editMut.isPending || !editContent.trim()}
                              className="p-1 text-green-400 hover:text-green-300 disabled:opacity-40"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => {
                                setEditingMsg(null);
                                setEditContent('');
                              }}
                              className="p-1 text-text-tertiary hover:text-text-primary"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <p className="text-[14px] text-text-primary leading-relaxed whitespace-pre-wrap break-words">
                            {msg.content}
                            {msg.edited_at && (
                              <span className="text-[11px] text-text-tertiary ml-1">(edited)</span>
                            )}
                          </p>
                        )}

                        {/* Hover actions */}
                        {!isEditing && (
                          <div className="absolute right-2 top-0 -translate-y-1/2 hidden group-hover:flex items-center gap-0.5 bg-krait-surface2 border border-krait-border rounded-lg shadow-md">
                            {isOwn && (
                              <>
                                <button
                                  onClick={() => {
                                    setEditingMsg(msg.message_id);
                                    setEditContent(msg.content);
                                  }}
                                  className="p-1.5 text-text-tertiary hover:text-text-primary transition-colors"
                                  title="Edit"
                                >
                                  <Edit3 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => {
                                    if (confirm('Delete this message?'))
                                      deleteMut.mutate(msg.message_id);
                                  }}
                                  disabled={deleteMut.isPending}
                                  className="p-1.5 text-text-tertiary hover:text-red-400 transition-colors"
                                  title="Delete"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* New messages button */}
          {!shouldAutoScroll.current && messages.length > 0 && (
            <div className="sticky bottom-2 flex justify-center">
              <button
                onClick={() => {
                  scrollToBottom();
                  shouldAutoScroll.current = true;
                }}
                className="bg-krait-surface3 border border-krait-borderHi rounded-full px-3 py-1.5 text-[12px] text-text-primary hover:bg-krait-borderHi shadow-lg flex items-center gap-1.5 transition-colors"
              >
                <ChevronDown className="w-3.5 h-3.5" /> New messages
              </button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input Area */}
        <div className="px-4 pb-4 pt-2 shrink-0">
          <div className="bg-krait-surface2 border border-krait-borderHi rounded-lg overflow-hidden focus-within:border-krait-borderHi transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Message #${room?.name ?? 'channel'}`}
              rows={1}
              className="w-full bg-transparent border-none text-[14px] text-text-primary placeholder:text-text-tertiary resize-none px-3 py-2.5 focus:outline-none max-h-[200px]"
            />
            <div className="flex items-center justify-between px-3 pb-1.5">
              <span className="text-[11px] text-text-tertiary">Shift + Enter for new line</span>
              <button
                onClick={handleSend}
                disabled={!input.trim() || sendMutation.isPending}
                className="px-3 py-1 bg-venom-yellow text-black text-[12px] font-semibold rounded-md hover:brightness-110 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
              >
                {sendMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <>
                    Send <Send className="w-3 h-3" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      <MembersPanel workspaceId={workspaceId} onlineUserIds={onlineUserIds} />
    </div>
  );
}
