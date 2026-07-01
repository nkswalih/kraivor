'use client';

import { MessagesSquare, Shield, FileText, Gauge, CheckCircle, BotMessageSquare } from 'lucide-react';
import { motion } from 'framer-motion';
import { AiInput } from '@/components/features/ai-input';
import type { ConversationSummary } from '@/lib/api/ai-api';

interface AiWelcomeProps {
  workspaceAvatar?: string | null;
  conversations: ConversationSummary[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onSuggestion: (text: string) => void;
  onLoadConversation: (id: string) => void;
  isStreaming: boolean;
  selectedModel: string;
  onModelSelect: (id: string) => void;
  showBanner: boolean;
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
  isStreaming,
  selectedModel,
  onModelSelect,
  showBanner,
}: AiWelcomeProps) {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[720px] mx-auto px-6 pt-16 pb-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, translateY: 16 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="text-center mb-8"
        >
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
        </motion.div>

        {/* Input */}
        <motion.div
          initial={{ opacity: 0, translateY: 16 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ duration: 0.4, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        >
          <AiInput
            value={input}
            onChange={onInputChange}
            onSend={onSend}
            onKeyDown={onKeyDown}
            isStreaming={isStreaming}
            selectedModel={selectedModel}
            onModelSelect={onModelSelect}
            showBanner={showBanner}
          />
        </motion.div>

        {/* Suggestions grid */}
        <motion.div
          initial={{ opacity: 0, translateY: 16 }}
          animate={{ opacity: 1, translateY: 0 }}
          transition={{ duration: 0.4, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="grid grid-cols-2 gap-8 mt-12"
        >
          <div>
            <div className="text-[10px] uppercase tracking-[0.12em] font-medium text-text-tertiary mb-3">
              RECENT CHATS
            </div>
            <div className="space-y-0.5">
              {conversations.length === 0 && (
                <p className="text-[13px] text-text-tertiary px-3 py-2">
                  No conversations yet
                </p>
              )}
              {conversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => onLoadConversation(conv.id)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-krait-surface3 transition-colors text-left group"
                >
                  <MessagesSquare
                    className="w-4 h-4 text-text-tertiary shrink-0 group-hover:text-text-secondary transition-colors"
                    strokeWidth={1.5}
                  />
                  <span className="text-[13px] text-text-secondary truncate group-hover:text-text-primary transition-colors">
                    {conv.title}
                  </span>
                </button>
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
        </motion.div>
      </div>
    </div>
  );
}
