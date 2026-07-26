'use client';

import Link from 'next/link';
import { createPortal } from 'react-dom';
import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Plus,
  SlidersHorizontal,
  ArrowUp,
  ArrowUpCircle,
  Square,
  Globe,
  FlaskConical,
  Paperclip,
  Search,
} from 'lucide-react';
import { ModelSelector, getModelIcon, getModelName } from '@/components/ai/ai-model-selector';
import { AiByokSetupDialog } from '@/components/ai/ai-byok-setup-dialog';
import { TokenUsageDonut } from '@/components/ai/ai-token-usage-donut';
import type { ModelItem } from '@/lib/api/ai-api';
import type { DailyUsage, ChatMode } from '@/types/domain/ai';

interface AiInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
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

const MAX_HEIGHT = 240;

const MODE_OPTIONS: { value: ChatMode; label: string; description: string; icon: typeof Globe }[] = [
  { value: 'normal', label: 'Normal', description: 'Fast responses, no web search', icon: Search },
  { value: 'web_search', label: 'Web Search', description: 'Search the web for answers', icon: Globe },
  { value: 'research', label: 'Research', description: 'Deep analysis with multiple sources', icon: FlaskConical },
];

export function AiInput({
  value,
  onChange,
  onSend,
  onKeyDown,
  isStreaming,
  selectedModel,
  onModelSelect,
  showBanner,
  models,
  onStop,
  dailyUsage,
  chatMode = 'normal',
  onModeChange,
}: AiInputProps) {
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showModeDropdown, setShowModeDropdown] = useState(false);
  const [popupPos, setPopupPos] = useState<{ top: number; left: number; above: boolean } | null>(null);
  const [modeDropdownPos, setModeDropdownPos] = useState<{ top: number; left: number } | null>(null);
  const [showByokSetup, setShowByokSetup] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const plusRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const modeDropdownRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* ─── Auto-resize textarea ───────────────────────────── */
  const autoResize = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    const newHeight = Math.min(ta.scrollHeight, MAX_HEIGHT);
    ta.style.height = `${newHeight}px`;
    ta.style.overflowY = ta.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden';
  }, []);

  useEffect(() => {
    autoResize();
  }, [value, autoResize]);

  /* ─── Keyboard handler ───────────────────────────────── */
  const handleKeyDownInner = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      onSend();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      onSend();
      return;
    }
    onKeyDown(e);
  };

  /* ─── Toggle model dropdown ─────────────────────────── */
  const toggleModelSelector = useCallback(() => {
    setShowModelSelector(prev => {
      if (prev) return false;
      const btn = buttonRef.current;
      if (!btn) return true;
      const rect = btn.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const above = spaceBelow < 420 && rect.top > spaceBelow;
      setPopupPos({
        top: above ? rect.top - 8 : rect.bottom + 8,
        left: Math.max(8, rect.right - 255),
        above,
      });
      return true;
    });
  }, []);

  /* ─── Toggle mode dropdown ──────────────────────────── */
  const toggleModeDropdown = useCallback(() => {
    setShowModeDropdown(prev => {
      if (prev) return false;
      const btn = plusRef.current;
      if (!btn) return true;
      const rect = btn.getBoundingClientRect();
      setModeDropdownPos({
        top: rect.top - 8,
        left: rect.left,
      });
      return true;
    });
  }, []);

  /* ─── Close on outside click / escape ────────────────── */
  useEffect(() => {
    if (!showModelSelector && !showModeDropdown) return;
    const handlePointerDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (popupRef.current?.contains(target) || buttonRef.current?.contains(target)) return;
      if (modeDropdownRef.current?.contains(target) || plusRef.current?.contains(target)) return;
      setShowModelSelector(false);
      setShowModeDropdown(false);
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowModelSelector(false);
        setShowModeDropdown(false);
      }
    };
    document.addEventListener('pointerdown', handlePointerDown, true);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown, true);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [showModelSelector, showModeDropdown]);

  /* ─── Listen for ai-open-byok event (from error actions) ── */
  useEffect(() => {
    const handler = () => setShowByokSetup(true);
    window.addEventListener('ai-open-byok', handler);
    return () => window.removeEventListener('ai-open-byok', handler);
  }, []);

  /* ─── Model select: check if BYOK → show setup dialog ──── */
  const handleModelSelect = (id: string) => {
    setShowModelSelector(false);
    const model = (models || []).find(m => m.id === id);
    if (model?.tier === 'byok') {
      setShowByokSetup(true);
      return;
    }
    onModelSelect(id);
  };

  /* ─── Mode select ───────────────────────────────────── */
  const handleModeSelect = (mode: ChatMode) => {
    setShowModeDropdown(false);
    onModeChange?.(mode);
  };

  /* ─── File attach (placeholder) ─────────────────────── */
  const handleFileClick = () => {
    setShowModeDropdown(false);
    fileInputRef.current?.click();
  };

  const currentMode = MODE_OPTIONS.find(m => m.value === chatMode);

  return (
    <div className="flex items-end gap-2.5 max-w-[720px] mx-auto">
      <div className="flex-1 min-w-0">
        {showBanner && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-950/40 border border-blue-800/30 border-b-0 rounded-t-[20px]">
            <ArrowUpCircle className="w-4 h-4 text-blue-400 shrink-0" strokeWidth={1.8} />
            <span className="text-[13px] text-[#f2f2f3]">
              You&rsquo;ve run out of free AI responses.{' '}
              <Link
                href="/pricing"
                className="text-blue-400 font-medium hover:text-blue-300 underline underline-offset-2 transition-colors"
              >
                Upgrade Kraivor AI
              </Link>
            </span>
          </div>
        )}

        <div
          className={`bg-krait-surface2 border border-krait-border/50 focus-within:border-venom-yellow/40 hover:border-krait-borderHi/70 transition-all duration-200 shadow-sm focus-within:shadow-[0_0_0_1px_rgba(250,204,21,0.06)] ${
            showBanner ? 'rounded-b-[20px] border-t-0' : 'rounded-[20px]'
          }`}
        >
          <div className="px-4 pt-3.5 min-h-[36px] flex items-start">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={e => onChange(e.target.value)}
              onKeyDown={handleKeyDownInner}
              placeholder="Do anything with AI..."
              rows={1}
              disabled={isStreaming}
              style={{ maxHeight: MAX_HEIGHT }}
              className="w-full bg-transparent border-none text-[14px] text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none py-0 leading-relaxed whitespace-pre-wrap break-words disabled:opacity-50 overflow-x-hidden"
            />
          </div>

          <div className="flex items-center justify-between px-4 pb-3 pt-2">
            <div className="flex items-center gap-2.5">
              {/* Mode selector (+) button */}
              <div className="relative">
                <button
                  ref={plusRef}
                  type="button"
                  disabled={isStreaming}
                  onClick={toggleModeDropdown}
                  className="flex items-center gap-1 text-text-tertiary hover:text-text-secondary transition-colors disabled:opacity-30"
                  title="Select mode"
                >
                  <Plus className="w-4 h-4" strokeWidth={1.8} />
                  {chatMode !== 'normal' && currentMode && (
                    <span className="flex items-center gap-0.5 px-1.5 py-0.5 bg-venom-yellow/10 border border-venom-yellow/20 rounded text-[10px] font-medium text-venom-yellow">
                      <currentMode.icon className="w-2.5 h-2.5" strokeWidth={2} />
                      {currentMode.label}
                    </span>
                  )}
                </button>
              </div>
              <button
                type="button"
                disabled={isStreaming}
                onClick={() => setShowByokSetup(true)}
                className="text-text-tertiary hover:text-text-secondary transition-colors disabled:opacity-30"
                title="Manage API Keys"
              >
                <SlidersHorizontal className="w-4 h-4" strokeWidth={1.8} />
              </button>
              <TokenUsageDonut usage={dailyUsage} size={16} />
            </div>
            {/* Ai model selector button*/}
            <div className="flex items-center gap-1.5">
              <button
                ref={buttonRef}
                type="button"
                onClick={toggleModelSelector}
                className="flex items-center gap-1.5 px-2 py-1 bg-krait-surface3 border border-krait-border/60 rounded-md hover:border-krait-borderHi transition-colors"
              >
                <span className="w-3.5 h-3.5 flex items-center justify-center shrink-0">
                  {getModelIcon(selectedModel)}
                </span>
                <span className="text-[12px] font-medium text-text-secondary">{getModelName(selectedModel)}</span>
              </button>
              {isStreaming ? (
                <button
                  type="button"
                  onClick={onStop}
                  className="w-6 h-6 rounded-full bg-venom-yellow text-black flex items-center justify-center shrink-0 hover:brightness-110 transition-all"
                  title="Stop generating"
                >
                  <Square className="w-2.5 h-2.5" fill="currentColor" strokeWidth={0} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onSend}
                  disabled={!value.trim()}
                  className="w-6 h-6 rounded-full bg-venom-yellow text-black flex items-center justify-center shrink-0 hover:brightness-110 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ArrowUp className="w-3 h-3" strokeWidth={2.5} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Mode dropdown (portal) */}
      {showModeDropdown && modeDropdownPos && createPortal(
        <div
          ref={modeDropdownRef}
          style={{
            position: 'fixed',
            bottom: `calc(100vh - ${modeDropdownPos.top}px)`,
            left: modeDropdownPos.left,
            zIndex: 2147483647,
          }}
          className="w-56"
          onPointerDown={e => e.stopPropagation()}
        >
          <div className="bg-krait-surface2 border border-krait-border/60 rounded-xl shadow-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-krait-border/40">
              <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">Mode</p>
            </div>
            <div className="p-1">
              {MODE_OPTIONS.map(opt => {
                const Icon = opt.icon;
                const isActive = chatMode === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleModeSelect(opt.value)}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-colors ${
                      isActive
                        ? 'bg-venom-yellow/10 text-venom-yellow'
                        : 'text-text-secondary hover:bg-krait-surface3 hover:text-text-primary'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" strokeWidth={1.8} />
                    <div className="min-w-0">
                      <div className="text-[12px] font-medium leading-tight">{opt.label}</div>
                      <div className="text-[10px] text-text-tertiary leading-tight mt-0.5">{opt.description}</div>
                    </div>
                    {isActive && (
                      <div className="ml-auto w-1.5 h-1.5 rounded-full bg-venom-yellow shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>
            <div className="border-t border-krait-border/40 p-1">
              <button
                type="button"
                onClick={handleFileClick}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left text-text-secondary hover:bg-krait-surface3 hover:text-text-primary transition-colors"
              >
                <Paperclip className="w-3.5 h-3.5 shrink-0" strokeWidth={1.8} />
                <div className="min-w-0">
                  <div className="text-[12px] font-medium leading-tight">Add Files</div>
                  <div className="text-[10px] text-text-tertiary leading-tight mt-0.5">Attach files or photos</div>
                </div>
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*,.pdf,.txt,.md,.csv,.json,.xml,.yaml,.yml"
        className="hidden"
        onChange={() => {/* TODO: handle file attach */}}
      />

      {/* Model selector (portal) */}
      {showModelSelector && popupPos && createPortal(
        <div
          ref={popupRef}
          style={{
            position: 'fixed',
            top: popupPos.above ? undefined : popupPos.top,
            bottom: popupPos.above ? `calc(100vh - ${popupPos.top}px)` : undefined,
            left: popupPos.left,
            zIndex: 2147483647,
          }}
          onPointerDown={e => e.stopPropagation()}
        >
          <ModelSelector selected={selectedModel} onSelect={handleModelSelect} models={models} />
        </div>,
        document.body,
      )}

      {showByokSetup && (
        <AiByokSetupDialog
          onClose={() => setShowByokSetup(false)}
          onSaved={() => setShowByokSetup(false)}
        />
      )}
    </div>
  );
}
