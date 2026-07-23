'use client';

import Link from 'next/link';
import { createPortal } from 'react-dom';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Plus, SlidersHorizontal, ArrowUp, ArrowUpCircle, Square } from 'lucide-react';
import { ModelSelector, getModelIcon, getModelName } from '@/components/features/model-selector';
import { ByokKeyDialog, ApiKeysPanel } from '@/components/features/byok-key-dialog';
import { TokenUsageDonut } from '@/components/features/token-usage-donut';
import type { ModelItem } from '@/lib/api/ai-api';
import type { DailyUsage } from '@/types/domain/ai';

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
}

const MAX_HEIGHT = 240;

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
}: AiInputProps) {
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [popupPos, setPopupPos] = useState<{ top: number; left: number; above: boolean } | null>(null);
  const [byokProvider, setByokProvider] = useState<string | null>(null);
  const [showApiKeysPanel, setShowApiKeysPanel] = useState(false);
  const [apiKeysEditProvider, setApiKeysEditProvider] = useState<string | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

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

  /* ─── Toggle dropdown (position via fixed + portal) ──── */
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
        left: Math.max(8, rect.right - 272),
        above,
      });
      return true;
    });
  }, []);

  /* ─── Close on outside click / escape ────────────────── */
  useEffect(() => {
    if (!showModelSelector) return;
    const handlePointerDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (popupRef.current?.contains(target) || buttonRef.current?.contains(target)) return;
      setShowModelSelector(false);
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowModelSelector(false);
    };
    document.addEventListener('pointerdown', handlePointerDown, true);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown, true);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [showModelSelector]);

  /* ─── Model select: check if BYOK → show key dialog ──── */
  const handleModelSelect = (id: string) => {
    setShowModelSelector(false);
    const model = (models || []).find(m => m.id === id);
    if (model?.tier === 'byok') {
      setByokProvider(model.provider);
      return;
    }
    onModelSelect(id);
  };

  const handleByokSave = () => {
    if (byokProvider) {
      const model = (models || []).find(m => m.provider === byokProvider && m.tier === 'byok');
      if (model) onModelSelect(model.id);
    }
    setByokProvider(null);
  };

  /* ─── Settings panel: edit provider → opens key dialog ── */
  const handleApiKeysEdit = (provider: string) => {
    setShowApiKeysPanel(false);
    setApiKeysEditProvider(provider);
  };

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
              <button
                type="button"
                disabled={isStreaming}
                className="text-text-tertiary hover:text-text-secondary transition-colors disabled:opacity-30"
              >
                <Plus className="w-4 h-4" strokeWidth={1.8} />
              </button>
              <button
                type="button"
                disabled={isStreaming}
                onClick={() => setShowApiKeysPanel(true)}
                className="text-text-tertiary hover:text-text-secondary transition-colors disabled:opacity-30"
                title="Manage API Keys"
              >
                <SlidersHorizontal className="w-4 h-4" strokeWidth={1.8} />
              </button>
              <TokenUsageDonut usage={dailyUsage} size={16} />
            </div>

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
                <div className="w-4 h-4 rounded-full border border-krait-borderHi flex items-center justify-center ml-0.5">
                  <ArrowUp className="w-2.5 h-2.5 text-text-tertiary" strokeWidth={2.5} />
                </div>
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

      {byokProvider && (
        <ByokKeyDialog
          provider={byokProvider}
          onClose={() => setByokProvider(null)}
          onSave={handleByokSave}
        />
      )}

      {showApiKeysPanel && (
        <ApiKeysPanel
          onClose={() => setShowApiKeysPanel(false)}
          onEdit={handleApiKeysEdit}
        />
      )}

      {apiKeysEditProvider && (
        <ByokKeyDialog
          provider={apiKeysEditProvider}
          onClose={() => setApiKeysEditProvider(null)}
          onSave={() => setApiKeysEditProvider(null)}
        />
      )}
    </div>
  );
}
