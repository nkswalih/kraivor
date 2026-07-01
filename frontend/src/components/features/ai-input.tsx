'use client';

import Link from 'next/link';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Plus, SlidersHorizontal, Sparkles, ArrowUp, ArrowUpCircle, X } from 'lucide-react';
import { ModelSelector, getModelIcon, getModelName, getModelGroup } from '@/components/features/model-selector';
import { aiApi } from '@/lib/api/ai-api';
import { toast } from 'sonner';

interface AiInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  isStreaming: boolean;
  selectedModel: string;
  onModelSelect: (id: string) => void;
  showBanner: boolean;
}

const MAX_HEIGHT = 260;

/* ─── API Key Dialog ──────────────────────────────────── */

function ApiKeyDialog({
  modelId,
  modelName,
  onClose,
  onSuccess,
}: {
  modelId: string;
  modelName: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);

  const providerMap: Record<string, string> = {
    'claude-sonnet': 'anthropic',
    'gpt-5o': 'openai',
    'deepseek-coder': 'openrouter',
    'grok-4': 'openrouter',
  };

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const provider = providerMap[modelId] ?? 'openrouter';
      await aiApi.provisionApiKey(provider);
      toast.success(`${modelName} activated`);
      onSuccess();
    } catch {
      toast.error('Failed to activate model. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#18181C] border border-[#27272A] rounded-xl p-5 max-w-sm w-full mx-4 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-venom-yellow" />
            <h3 className="text-[14px] font-semibold text-[#f2f2f3]">{modelName}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-[#5e5e72] hover:text-[#f2f2f3] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[12px] text-[#9898a6] mb-4">
          Activate {modelName} through Kraivor AI. Provider access is managed via your workspace plan.
        </p>
        <div className="flex items-center gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-md border border-[#27272A] text-[12px] text-[#9898a6] hover:text-[#f2f2f3] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-3 py-1.5 rounded-md bg-venom-yellow text-black text-[12px] font-medium hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Activating...' : 'Activate'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main Component ──────────────────────────────────── */

export function AiInput({
  value,
  onChange,
  onSend,
  onKeyDown,
  isStreaming,
  selectedModel,
  onModelSelect,
  showBanner,
}: AiInputProps) {
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [popupAbove, setPopupAbove] = useState(false);
  const [apiKeyDialog, setApiKeyDialog] = useState<string | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  /* ─── Choose up/down based on available viewport space ──── */
  useEffect(() => {
    if (!showModelSelector) return;
    const btn = buttonRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    setPopupAbove(spaceBelow < 320 && spaceAbove > spaceBelow);
  }, [showModelSelector]);

  /* ─── Close model selector on outside click ──────────────── */
  useEffect(() => {
    if (!showModelSelector) return;
    const handleClick = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        setShowModelSelector(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showModelSelector]);

  const handleModelSelect = (id: string) => {
    setShowModelSelector(false);
    const group = getModelGroup(id);
    if (group === 'api-key') {
      setApiKeyDialog(id);
    } else {
      onModelSelect(id);
    }
  };

  const dialogModel = apiKeyDialog ? getModelName(apiKeyDialog) : '';

  return (
    <div className="flex items-end gap-2.5 max-w-[720px] mx-auto">
      {/* Joined banner + input block */}
      <div className="flex-1 min-w-0">
        {/* Banner (free plan alert) — top-outer corners rounded, bottom flat */}
        {showBanner && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-950/40 border border-blue-800/30 border-b-0 rounded-t-2xl">
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

        {/* Main input container */}
        <div
          className={`bg-krait-surface2 border border-krait-border focus-within:border-krait-borderHi transition-colors ${
            showBanner ? 'rounded-b-2xl border-t-0' : 'rounded-2xl'
          }`}
        >
          {/* Textarea area */}
          <div className="px-4 pt-3.5">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={e => {
                onChange(e.target.value);
              }}
              onKeyDown={handleKeyDownInner}
              placeholder="Do anything with AI..."
              rows={1}
              disabled={isStreaming}
              style={{ maxHeight: MAX_HEIGHT }}
              className="w-full bg-transparent border-none text-[14px] text-text-primary placeholder:text-text-tertiary resize-none focus:outline-none py-0 leading-relaxed whitespace-pre-wrap break-words disabled:opacity-50"
            />
          </div>

          {/* Bottom row: icons left, model pill right */}
          <div className="flex items-center justify-between px-4 pb-3 pt-2 relative">
            {/* Left: Action Icons */}
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
                className="text-text-tertiary hover:text-text-secondary transition-colors disabled:opacity-30"
              >
                <SlidersHorizontal className="w-4 h-4" strokeWidth={1.8} />
              </button>
            </div>

            {/* Right: Model Pill */}
            <div ref={buttonRef}>
              <button
                type="button"
                onClick={() => setShowModelSelector(v => !v)}
                className="flex items-center gap-1.5 px-2 py-1 bg-krait-surface3 border border-krait-border rounded-md hover:border-krait-borderHi transition-colors"
              >
                <span className="w-3.5 h-3.5 flex items-center justify-center shrink-0">
                  {getModelIcon(selectedModel)}
                </span>
                <span className="text-[12px] font-medium text-text-secondary">{getModelName(selectedModel)}</span>
                <div className="w-4 h-4 rounded-full border border-krait-borderHi flex items-center justify-center ml-0.5">
                  <ArrowUp className="w-2.5 h-2.5 text-text-tertiary" strokeWidth={2.5} />
                </div>
              </button>
            </div>

            {/* Model selector popup (flips up/down based on space) */}
            {showModelSelector && (
              <div
                ref={popupRef}
                className={`absolute right-0 z-50 ${
                  popupAbove ? 'bottom-full mb-2' : 'top-full mt-2'
                }`}
              >
                <ModelSelector selected={selectedModel} onSelect={handleModelSelect} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Floating send button (outside container) */}
      <button
        onClick={onSend}
        disabled={!value.trim() || isStreaming}
        className="w-10 h-10 rounded-full bg-venom-yellow text-black flex items-center justify-center shrink-0 hover:brightness-110 transition-all disabled:opacity-30 disabled:cursor-not-allowed mb-[1px]"
      >
        <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
      </button>

      {/* API Key Dialog */}
      {apiKeyDialog && (
        <ApiKeyDialog
          modelId={apiKeyDialog}
          modelName={dialogModel}
          onClose={() => setApiKeyDialog(null)}
          onSuccess={() => {
            onModelSelect(apiKeyDialog);
            setApiKeyDialog(null);
          }}
        />
      )}
    </div>
  );
}
