'use client';

import { useState, useCallback, memo } from 'react';
import { motion } from 'framer-motion';
import {
  Copy,
  Check,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  Share2,
  FileJson,
  Pencil,
  BotMessageSquare,
} from 'lucide-react';
import { SnakeIcon } from '@/components/features/ai-snake-icon';
import { AiMarkdown } from '@/components/features/ai-markdown';
import { ThinkingIndicator } from '@/components/features/ai-thinking-indicator';
import type { ChatMessage } from '@/types/domain/ai';
import { MessageRole, MessageStatus } from '@/types/domain/ai';

interface AiMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
  thinkingStatus?: string;
  onRegenerate?: () => void;
  onEdit?: (content: string) => void;
}

/* ─── Main component ─────────────────────────────────── */

export const AiMessage = memo(function AiMessage({
  message,
  isStreaming,
  thinkingStatus,
  onRegenerate,
  onEdit,
}: AiMessageProps) {
  const isUser = message.role === MessageRole.USER;
  const isError = message.status === MessageStatus.ERROR;
  const isThinking = isStreaming && !message.content;
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  }, [message.content]);

  return (
    <motion.div
      initial={{ opacity: 0, translateY: 12, scale: 0.98 }}
      animate={{ opacity: 1, translateY: 0, scale: 1 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="group/message relative"
    >
      {/* Error state */}
      {isError ? (
        <div className="mx-auto max-w-[720px] px-4">
          <div className="rounded-xl border border-red-900/40 bg-red-950/20 p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-red-900/30 flex items-center justify-center shrink-0">
                <BotMessageSquare className="w-4 h-4 text-red-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-red-300 mb-1">
                  Response failed
                </p>
                <p className="text-[13px] text-red-400/80 leading-relaxed">
                  {message.content || 'An unexpected error occurred.'}
                </p>
                {onRegenerate && (
                  <button
                    onClick={onRegenerate}
                    className="mt-3 flex items-center gap-1.5 text-[12px] text-red-300 hover:text-red-200 transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
                    Try again
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* ── User message ── */}
          {isUser ? (
            <div className="mx-auto max-w-[720px] px-4">
              <div className="flex justify-end py-2">
                <div className="group/user-msg max-w-[80%]">
                  <div className="bg-krait-surface3 border border-krait-border rounded-2xl rounded-br-md px-4 py-2.5">
                    <div className="text-[14px] text-text-primary leading-relaxed">
                      <AiMarkdown content={message.content} />
                    </div>
                  </div>

                  {/* User message actions */}
                  <div className="flex items-center justify-end gap-0.5 pt-1 pr-1 opacity-0 group-hover/user-msg:opacity-100 transition-opacity duration-200">
                    <ActionButton
                      icon={copied ? Check : Copy}
                      label={copied ? 'Copied' : 'Copy'}
                      onClick={handleCopy}
                      active={copied}
                    />
                    {onEdit && (
                      <ActionButton
                        icon={Pencil}
                        label="Edit"
                        onClick={() => onEdit(message.content)}
                      />
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* ── Assistant message ── */
            <div className="mx-auto max-w-[720px] px-4">
              <div className="py-3">
                {/* Thinking state — no header, minimal layout */}
                {isThinking ? (
                  <ThinkingIndicator status={thinkingStatus} />
                ) : (
                  <>
                    {/* Header — visible when content is streaming or complete */}
                    <div className="flex items-center gap-2 mb-1.5">
                      <SnakeIcon />
                      {/* <span className="text-[13px] font-semibold text-text-primary">
                        Kraivor AI
                      </span> */}
                      {message.timestamp && (
                        <span className="text-[11px] text-text-tertiary">
                          {new Date(message.timestamp).toLocaleTimeString([], {
                            hour: 'numeric',
                            minute: '2-digit',
                            hour12: true,
                          })}
                        </span>
                      )}
                    </div>

                    {/* Content */}
                    <div className="ml-8">
                      {isStreaming ? (
                        <div className="text-[14px] text-text-primary leading-relaxed whitespace-pre-wrap">
                          {message.content}
                          <span className="inline-block w-[2px] h-[1em] bg-yellow-300/70 ml-[1px] align-text-bottom animate-pulse" />
                        </div>
                      ) : (
                        <AiMarkdown content={message.content} />
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Assistant actions — only when content is complete */}
              {!isStreaming && message.content && (
                <div className="flex items-center gap-0.5 ml-[3.25rem] pb-2 opacity-0 group-hover/message:opacity-100 focus-within:opacity-100 transition-opacity duration-200">
                  <ActionButton
                    icon={copied ? Check : Copy}
                    label={copied ? 'Copied' : 'Copy'}
                    onClick={handleCopy}
                    active={copied}
                  />
                  {onRegenerate && (
                    <ActionButton
                      icon={RefreshCw}
                      label="Regenerate"
                      onClick={onRegenerate}
                    />
                  )}
                  <ActionButton icon={ThumbsUp} label="Good response" />
                  <ActionButton icon={ThumbsDown} label="Bad response" />
                  <ActionButton icon={Share2} label="Share" disabled />
                  <ActionButton icon={FileJson} label="Open in Canvas" disabled />
                </div>
              )}
            </div>
          )}
        </>
      )}
    </motion.div>
  );
});

/* ─── Action button ──────────────────────────────────── */

function ActionButton({
  icon: Icon,
  label,
  onClick,
  active,
  disabled,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  label: string;
  onClick?: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className={`p-1.5 rounded-md transition-all ${
        active
          ? 'text-venom-yellow bg-venom-yellow/10'
          : 'text-text-tertiary hover:text-text-secondary hover:bg-krait-surface3'
      } ${disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
    </button>
  );
}
