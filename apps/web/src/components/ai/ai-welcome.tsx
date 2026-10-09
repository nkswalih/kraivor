'use client';

import { BotMessageSquare } from 'lucide-react';
import { AiInput } from '@/components/ai/ai-input';
import type { ModelItem } from '@/lib/api/ai-api';
import type { DailyUsage, ChatMode } from '@/types/domain/ai';

interface AiWelcomeProps {
  workspaceAvatar?: string | null;
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onSuggestion: (text: string) => void;
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
  { id: 's1', text: 'Analyze security vulnerabilities' },
  { id: 's2', text: 'Generate architecture blueprint' },
  { id: 's3', text: 'Audit performance issues' },
  { id: 's4', text: 'Review code style consistency' },
  { id: 's5', text: 'Explain codebase structure' },
  { id: 's6', text: 'Find and fix bugs' },
];

export function AiWelcome({
  workspaceAvatar,
  input,
  onInputChange,
  onSend,
  onKeyDown,
  onSuggestion,
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
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
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
      <div className="w-full max-w-[720px] animate-fade-up" style={{ animationDelay: '0.1s' }}>
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

      {/* Suggestion Chips */}
      <div className="flex flex-wrap gap-2 mt-6 justify-center max-w-[720px] animate-fade-up" style={{ animationDelay: '0.2s' }}>
        {SUGGESTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => onSuggestion(s.text)}
            className="px-4 py-2 bg-krait-surface2 border border-krait-border/50 rounded-full text-[13px] text-text-secondary hover:bg-krait-surface3 hover:text-text-primary hover:border-krait-borderHi transition-all duration-200"
          >
            {s.text}
          </button>
        ))}
      </div>
    </div>
  );
}
