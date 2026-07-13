'use client';

import { useState, useEffect, useMemo } from 'react';
import { Lightning } from '@phosphor-icons/react';
import type { ReactNode } from 'react';
import type { ModelItem, ModelTier } from '@/lib/api/ai-api';
import { aiApi } from '@/lib/api/ai-api';
import { MODEL_ICONS, KraitIcon } from './model-icons';

/* ─── Fallback models (static, if API fails) ────────────── */

const FALLBACK_MODELS: ModelItem[] = [
  // ── Kraivor AI (free, built-in) ──
  { id: 'krait-2.0', name: 'Krait 2.0', tier: 'kraivor', provider: 'kraivor', backendModel: 'openrouter/auto', latency: '0.4s', context: '128K' },

  // ── Free Models (OpenRouter) ──
  { id: 'cohere-north-mini-code', name: 'Cohere North Mini', tier: 'free', provider: 'cohere', backendModel: 'cohere/north-mini-code:free', latency: '0.6s', context: '128K' },
  { id: 'nvidia-nemotron-ultra', name: 'Nvidia Nemotron Ultra', tier: 'free', provider: 'nvidia', backendModel: 'nvidia/nemotron-3-ultra-550b-a55b:free', latency: '2.0s', context: '1M' },
  { id: 'tencent-hy3', name: 'Tencent HY3', tier: 'free', provider: 'tencent', backendModel: 'tencent/hy3:free', latency: '3.4s', context: '262K' },
  { id: 'poolside-laguna-xs', name: 'Poolside Laguna XS', tier: 'free', provider: 'poolside', backendModel: 'poolside/laguna-xs-2.1:free', latency: '0.8s', context: '128K' },
  { id: 'poolside-laguna-m', name: 'Poolside Laguna M', tier: 'free', provider: 'poolside', backendModel: 'poolside/laguna-m.1:free', latency: '1.2s', context: '128K' },
  { id: 'nvidia-nemotron-super', name: 'Nvidia Nemotron Super', tier: 'free', provider: 'nvidia', backendModel: 'nvidia/nemotron-3-super-120b-a12b:free', latency: '2.5s', context: '128K' },
  { id: 'google-gemma-4', name: 'Google Gemma 4', tier: 'free', provider: 'google', backendModel: 'google/gemma-4-31b-it:free', latency: '1.0s', context: '128K' },
  { id: 'nvidia-nemotron-nano', name: 'Nvidia Nemotron Nano', tier: 'free', provider: 'nvidia', backendModel: 'nvidia/nemotron-3-nano-30b-a3b:free', latency: '0.6s', context: '128K' },
  { id: 'openai-gpt-oss', name: 'OpenAI GPT OSS', tier: 'free', provider: 'openai', backendModel: 'openai/gpt-oss-120b:free', latency: '1.8s', context: '128K' },

  // ── BYOK Models (per-provider keys, OpenRouter fallback) ──
  // Anthropic
  { id: 'claude-fable-5', name: 'Claude Fable 5', tier: 'byok', provider: 'anthropic', backendModel: 'anthropic/claude-fable-5', latency: '1.5s', context: '200K' },
  { id: 'claude-opus-4-8', name: 'Claude Opus 4.8', tier: 'byok', provider: 'anthropic', backendModel: 'anthropic/claude-opus-4-8', latency: '2.0s', context: '200K' },
  { id: 'claude-opus-4-7', name: 'Claude Opus 4.7', tier: 'byok', provider: 'anthropic', backendModel: 'anthropic/claude-opus-4-7', latency: '2.2s', context: '200K' },
  { id: 'claude-sonnet-5', name: 'Claude Sonnet 5', tier: 'byok', provider: 'anthropic', backendModel: 'anthropic/claude-sonnet-5', latency: '1.2s', context: '200K' },
  { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', tier: 'byok', provider: 'anthropic', backendModel: 'anthropic/claude-sonnet-4-6', latency: '1.0s', context: '200K' },
  // OpenAI
  { id: 'gpt-5.6-sol', name: 'GPT-5.6 Sol', tier: 'byok', provider: 'openai', backendModel: 'openai/gpt-5.6-sol', latency: '1.0s', context: '128K' },
  { id: 'gpt-5.6-terra', name: 'GPT-5.6 Terra', tier: 'byok', provider: 'openai', backendModel: 'openai/gpt-5.6-terra', latency: '1.2s', context: '128K' },
  { id: 'gpt-5.5', name: 'GPT-5.5', tier: 'byok', provider: 'openai', backendModel: 'openai/gpt-5.5', latency: '0.9s', context: '128K' },
  { id: 'gpt-5.4', name: 'GPT-5.4', tier: 'byok', provider: 'openai', backendModel: 'openai/gpt-5.4', latency: '0.8s', context: '128K' },
  // Google
  { id: 'gemini-3.5-flash', name: 'Gemini 3.5 Flash', tier: 'byok', provider: 'google', backendModel: 'google/gemini-3.5-flash', latency: '0.5s', context: '1M' },
  { id: 'gemini-3.1-pro', name: 'Gemini 3.1 Pro', tier: 'byok', provider: 'google', backendModel: 'google/gemini-3.1-pro', latency: '1.5s', context: '1M' },
  // DeepSeek
  { id: 'deepseek-v4-pro', name: 'DeepSeek V4 Pro', tier: 'byok', provider: 'deepseek', backendModel: 'deepseek/deepseek-v4-pro', latency: '1.0s', context: '128K' },
  // xAI
  { id: 'grok-4.3', name: 'Grok 4.3', tier: 'byok', provider: 'xai', backendModel: 'xai/grok-4.3', latency: '1.5s', context: '128K' },
];

/* ─── Group config ──────────────────────────────────────── */

const GROUP_ORDER: { tier: ModelTier; label: string; icon: ReactNode }[] = [
  { tier: 'kraivor', label: 'Kraivor AI', icon: <KraitIcon /> },
  { tier: 'free', label: 'Free Models', icon: null },
  { tier: 'byok', label: 'BYOK Models', icon: null },
];

/* ─── Component props ───────────────────────────────────── */

export interface ModelSelectorProps {
  selected: string;
  onSelect: (id: string) => void;
  models?: ModelItem[];
}

/* ─── Component ────────────────────────────────────────── */

export function ModelSelector({ selected, onSelect, models: modelsProp }: ModelSelectorProps) {
  const [fetchedModels, setFetchedModels] = useState<ModelItem[] | null>(null);
  const [loading, setLoading] = useState(!modelsProp);

  useEffect(() => {
    if (modelsProp) return;
    let cancelled = false;
    setLoading(true);
    aiApi
      .listModels()
      .then(data => {
        if (!cancelled) setFetchedModels(data);
      })
      .catch(() => {
        if (!cancelled) setFetchedModels(FALLBACK_MODELS);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [modelsProp]);

  const allModels = (Array.isArray(modelsProp) && modelsProp.length > 0)
    ? modelsProp
    : Array.isArray(fetchedModels) && fetchedModels.length > 0
      ? fetchedModels
      : FALLBACK_MODELS;

  const grouped = useMemo(() => {
    const map = new Map<ModelTier, ModelItem[]>();
    for (const m of allModels) {
      const arr = map.get(m.tier) ?? [];
      arr.push(m);
      map.set(m.tier, arr);
    }
    return map;
  }, [allModels]);

  if (loading) {
    return (
      <div className="w-64 bg-[#18181C] border border-[#27272A] rounded-xl shadow-2xl p-4 flex items-center justify-center">
        <span className="text-[12px] text-[#5e5e72] animate-pulse">Loading models...</span>
      </div>
    );
  }

  let hasPrev = false;

  return (
    <div
      className="w-64 bg-[#18181C] border border-[#27272A] rounded-xl shadow-2xl pointer-events-auto"
      onPointerDown={e => e.stopPropagation()}
    >
      <div className="max-h-[400px] overflow-y-auto overflow-x-hidden">
        {GROUP_ORDER.map(({ tier, label, icon: groupIcon }) => {
          const models = grouped.get(tier);
          if (!models || models.length === 0) return null;

          if (hasPrev) {
            return (
              <div key={tier}>
                <div className="border-t border-[#27272A] mx-3" />
                <GroupHeader label={label} icon={groupIcon} tier={tier} />
                <div className="pb-1.5">
                  {models.map(m => (
                    <ModelRow key={m.id} model={m} selected={selected} onSelect={onSelect} />
                  ))}
                </div>
              </div>
            );
          }

          hasPrev = true;
          return (
            <div key={tier}>
              <GroupHeader label={label} icon={groupIcon} tier={tier} />
              <div className="pb-1.5">
                {models.map(m => (
                  <ModelRow key={m.id} model={m} selected={selected} onSelect={onSelect} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Group header ──────────────────────────────────────── */

function GroupHeader({ label, icon }: { label: string; icon: ReactNode; tier: ModelTier }) {
  return (
    <div className="flex items-center gap-1.5 px-3 pt-3 pb-1">
      {icon && <span className="w-4 h-4 flex items-center justify-center">{icon}</span>}
      <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-[#5e5e72]">
        {label}
      </span>
    </div>
  );
}

/* ─── Model row ────────────────────────────────────────── */

function ModelRow({
  model,
  selected,
  onSelect,
}: {
  model: ModelItem;
  selected: string;
  onSelect: (id: string) => void;
}) {
  const active = selected === model.id;
  const iconFn = MODEL_ICONS[model.id];
  const IconComponent = iconFn ? iconFn() : null;

  return (
    <button
      onPointerDown={e => e.stopPropagation()}
      onClick={() => onSelect(model.id)}
      className={`w-full flex items-center gap-2.5 px-3 py-[7px] text-left transition-all duration-150 ${
        active
          ? 'bg-[#1f1f24] text-venom-yellow'
          : 'text-[#9898a6] hover:bg-[#1f1f24] hover:text-[#f2f2f3]'
      }`}
    >
      <span className="w-4 h-4 flex items-center justify-center shrink-0">
        {IconComponent}
      </span>
      <span className="text-[13px] font-medium flex-1 truncate">{model.name}</span>
    </button>
  );
}

/* ─── Exports (backward compat) ─────────────────────────── */

export function getModelIcon(id: string) {
  const fn = MODEL_ICONS[id];
  if (fn) return fn();
  return <KraitIcon />;
}

export function getModelName(id: string) {
  const m = FALLBACK_MODELS.find(m => m.id === id);
  return m?.name ?? id;
}

export function getModelGroup(id: string): ModelTier {
  const m = FALLBACK_MODELS.find(m => m.id === id);
  return m?.tier ?? 'kraivor';
}
