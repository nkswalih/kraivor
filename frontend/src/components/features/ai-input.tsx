'use client';

import { useState, useRef, useEffect } from 'react';
import { Plus, SlidersHorizontal, Sparkles, ArrowUp, ArrowUpCircle } from 'lucide-react';
import { ModelSelector, getModelIcon } from '@/components/features/model-selector';

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
  const popupRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLDivElement>(null);

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
    onModelSelect(id);
    setShowModelSelector(false);
  };

  return (
    <div className="flex items-end gap-2.5 max-w-[720px] mx-auto">
      {/* Joined banner + input block */}
      <div className="flex-1">
        {/* Banner (free plan alert) — top-outer corners rounded, bottom flat */}
        {showBanner && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-950/40 border border-blue-800/30 border-b-0 rounded-t-2xl">
            <ArrowUpCircle className="w-4 h-4 text-blue-400 shrink-0" strokeWidth={1.8} />
            <span className="text-[13px] text-[#f2f2f3]">
              You&rsquo;ve run out of free AI responses.{' '}
              <a href="/pricing" className="text-blue-400 font-medium hover:text-blue-300 underline underline-offset-2 transition-colors">
                Upgrade Kraivor AI
              </a>
            </span>
          </div>
        )}

        {/* Main input container — flat top where it touches banner, bottom-outer corners rounded */}
        <div
          className={`bg-[#18181C] border border-[#27272A] focus-within:border-[#3A3A3D] transition-colors ${
            showBanner ? 'rounded-b-2xl border-t-0' : 'rounded-2xl'
          }`}
        >
          {/* Top row: textarea fills full width */}
          <div className="px-4 pt-3.5">
            <textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Do anything with AI..."
              rows={1}
              disabled={isStreaming}
              className="w-full bg-transparent border-none text-[14px] text-[#d1d5db] placeholder:text-[#5e5e72] resize-none focus:outline-none py-0 leading-relaxed disabled:opacity-50"
            />
          </div>

          {/* Bottom row: icons left, model pill right */}
          <div className="flex items-center justify-between px-4 pb-3 pt-2 relative">
            {/* Left: Action Icons */}
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                disabled={isStreaming}
                className="text-[#5e5e72] hover:text-[#9898a6] transition-colors disabled:opacity-30"
              >
                <Plus className="w-4 h-4" strokeWidth={1.8} />
              </button>
              <button
                type="button"
                disabled={isStreaming}
                className="text-[#5e5e72] hover:text-[#9898a6] transition-colors disabled:opacity-30"
              >
                <SlidersHorizontal className="w-4 h-4" strokeWidth={1.8} />
              </button>
            </div>

            {/* Right: Model Pill */}
            <div ref={buttonRef}>
              <button
                type="button"
                onClick={() => setShowModelSelector(v => !v)}
                className="flex items-center gap-1.5 px-2 py-1 bg-[#1f1f24] border border-[#2c2c33] rounded-md hover:border-[#3d3d47] transition-colors"
              >
                <span className="w-3.5 h-3.5 flex items-center justify-center shrink-0">
                  {getModelIcon(selectedModel)}
                </span>
                <span className="text-[12px] font-medium text-[#9898a6]">{selectedModel}</span>
                <div className="w-4 h-4 rounded-full border border-[#3d3d47] flex items-center justify-center ml-0.5">
                  <ArrowUp className="w-2.5 h-2.5 text-[#5e5e72]" strokeWidth={2.5} />
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
        className="w-10 h-10 rounded-full bg-venom-yellow text-black flex items-center justify-center shrink-0 hover:brightness-110 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
      </button>
    </div>
  );
}
