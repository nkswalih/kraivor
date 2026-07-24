'use client';

import { createPortal } from 'react-dom';
import { useState, useEffect, useCallback } from 'react';
import {
  Key,
  X,
  Check,
  AlertTriangle,
  Loader2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Globe,
  Shield,
  RotateCw,
} from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';

/* ─── Types ─────────────────────────────────────────────── */

interface ProviderStatus {
  name: string;
  has_key: boolean;
  last_validated: string | null;
  custom_url: string | null;
}

interface ModelAssignment {
  model_id: string;
  display_name: string;
  provider: string;
  providers: string[];
}

/* ─── Provider metadata ─────────────────────────────────── */

const PROVIDERS: Record<string, { name: string; placeholder: string; color: string; docsUrl: string }> = {
  anthropic: { name: 'Anthropic', placeholder: 'sk-ant-api03-...', color: '#D97757', docsUrl: 'https://console.anthropic.com/settings/keys' },
  openai: { name: 'OpenAI', placeholder: 'sk-proj-...', color: '#10A37F', docsUrl: 'https://platform.openai.com/api-keys' },
  google: { name: 'Google AI', placeholder: 'AIza...', color: '#4285F4', docsUrl: 'https://aistudio.google.com/apikey' },
  deepseek: { name: 'DeepSeek', placeholder: 'sk-...', color: '#4D6BFE', docsUrl: 'https://platform.deepseek.com/api_keys' },
  xai: { name: 'xAI', placeholder: 'xai-...', color: '#FFFFFF', docsUrl: 'https://console.x.ai/' },
  groq: { name: 'Groq', placeholder: 'gsk_...', color: '#F55036', docsUrl: 'https://console.groq.com/keys' },
  openrouter: { name: 'OpenRouter', placeholder: 'sk-or-v1-...', color: '#8B5CF6', docsUrl: 'https://openrouter.ai/keys' },
};

const PROVIDER_ORDER = ['anthropic', 'openai', 'google', 'groq', 'deepseek', 'xai', 'openrouter'];

const MODEL_DISPLAY_NAMES: Record<string, string> = {
  'claude-fable-5': 'Claude Fable 5',
  'claude-opus-4-8': 'Claude Opus 4.8',
  'claude-opus-4-7': 'Claude Opus 4.7',
  'claude-sonnet-5': 'Claude Sonnet 5',
  'claude-sonnet-4-6': 'Claude Sonnet 4.6',
  'gpt-5.6-sol': 'GPT-5.6 Sol',
  'gpt-5.6-terra': 'GPT-5.6 Terra',
  'gpt-5.5': 'GPT-5.5',
  'gpt-5.4': 'GPT-5.4',
  'gemini-3.5-flash': 'Gemini 3.5 Flash',
  'gemini-3.1-pro': 'Gemini 3.1 Pro',
  'deepseek-v4-pro': 'DeepSeek V4 Pro',
  'grok-4.3': 'Grok 4.3',
};

/* ─── Helper ────────────────────────────────────────────── */

function jwtFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = useAuthStore.getState().accessToken;
  return fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers as Record<string, string>),
    },
  });
}

/* ─── Main Component ────────────────────────────────────── */

interface AiByokSetupDialogProps {
  onClose: () => void;
  onSaved?: () => void;
}

export function AiByokSetupDialog({ onClose, onSaved }: AiByokSetupDialogProps) {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [models, setModels] = useState<ModelAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [customUrlInput, setCustomUrlInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set());

  /* ── Load data ─────────────────────────────────────────── */

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [provRes, modelRes] = await Promise.all([
        jwtFetch('/api/ai/v1/byok/providers'),
        jwtFetch('/api/ai/v1/byok/models'),
      ]);
      if (provRes.ok) {
        const data = await provRes.json();
        setProviders(data.providers || []);
      }
      if (modelRes.ok) {
        const data = await modelRes.json();
        setModels(data.models || []);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  /* ── Keyboard ──────────────────────────────────────────── */

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  /* ── Save key ──────────────────────────────────────────── */

  const handleSaveKey = async () => {
    if (!editingProvider) return;
    if (!apiKeyInput.trim()) {
      setError('Please enter an API key');
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const res = await jwtFetch(`/api/ai/v1/byok/providers/${editingProvider}`, {
        method: 'POST',
        body: JSON.stringify({ api_key: apiKeyInput.trim(), custom_url: customUrlInput.trim() || null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.message || 'Failed to save key');
      }
      setSuccess('Key saved and validated');
      setApiKeyInput('');
      setCustomUrlInput('');
      setEditingProvider(null);
      await loadData();
      onSaved?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save key');
    } finally {
      setSaving(false);
    }
  };

  /* ── Validate key ──────────────────────────────────────── */

  const handleValidate = async (provider: string) => {
    setValidating(true);
    try {
      await jwtFetch(`/api/ai/v1/byok/providers/${provider}/validate`, { method: 'POST' });
      await loadData();
    } catch {
      // silent
    } finally {
      setValidating(false);
    }
  };

  /* ── Remove key ────────────────────────────────────────── */

  const handleRemove = async (provider: string) => {
    try {
      await jwtFetch(`/api/ai/v1/byok/providers/${provider}`, { method: 'DELETE' });
      await loadData();
      onSaved?.();
    } catch {
      // silent
    }
  };

  /* ── Update model provider ─────────────────────────────── */

  const handleModelProviderChange = async (modelId: string, provider: string) => {
    try {
      await jwtFetch(`/api/ai/v1/byok/models/${modelId}`, {
        method: 'PUT',
        body: JSON.stringify({ provider }),
      });
      setModels(prev => prev.map(m => m.model_id === modelId ? { ...m, provider } : m));
    } catch {
      // silent
    }
  };

  /* ── Toggle expanded ───────────────────────────────────── */

  const toggleExpanded = (provider: string) => {
    setExpandedProviders(prev => {
      const next = new Set(prev);
      if (next.has(provider)) next.delete(provider);
      else next.add(provider);
      return next;
    });
  };

  /* ── Render ────────────────────────────────────────────── */

  return createPortal(
    <div className="fixed inset-0 z-[2147483647] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Dialog */}
      <div
        className="relative w-full max-w-[560px] mx-4 bg-[#141416] border border-[#27272A] rounded-2xl shadow-2xl overflow-hidden max-h-[85vh] flex flex-col"
        onPointerDown={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-[#27272A] shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--venom-yellow)]/10 flex items-center justify-center">
              <Key className="w-4 h-4 text-[var(--venom-yellow)]" strokeWidth={2} />
            </div>
            <div>
              <h3 className="text-[14px] font-semibold text-[#f2f2f3]">AI Providers</h3>
              <p className="text-[11px] text-[#5e5e72]">Manage keys and model routing</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-md flex items-center justify-center text-[#5e5e72] hover:text-[#f2f2f3] hover:bg-[#27272A] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="px-5 py-12 flex items-center justify-center">
              <Loader2 className="w-5 h-5 text-[#5e5e72] animate-spin" />
            </div>
          ) : (
            <>
              {/* Provider Cards */}
              <div className="px-5 pt-4 pb-2">
                <p className="text-[11px] font-semibold tracking-[0.06em] uppercase text-[#5e5e72] mb-2">
                  Providers
                </p>
              </div>

              <div className="px-5 space-y-1.5">
                {PROVIDER_ORDER.map(key => {
                  const meta = PROVIDERS[key];
                  const status = providers.find(p => p.name === key);
                  const hasKey = status?.has_key ?? false;
                  const isEditing = editingProvider === key;
                  const isExpanded = expandedProviders.has(key);

                  return (
                    <div key={key} className="border border-[#27272A] rounded-xl overflow-hidden">
                      {/* Provider row */}
                      <div className="flex items-center gap-3 px-4 py-3 hover:bg-[#1f1f24] transition-colors">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                          style={{ backgroundColor: `${meta.color}15` }}
                        >
                          <Key className="w-4 h-4" style={{ color: meta.color }} strokeWidth={2} />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[13px] font-medium text-[#f2f2f3]">{meta.name}</span>
                            {hasKey && (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 text-[10px] font-medium">
                                <Check className="w-2.5 h-2.5" /> Active
                              </span>
                            )}
                          </div>
                          {hasKey && status?.custom_url && (
                            <div className="flex items-center gap-1 mt-0.5">
                              <Globe className="w-2.5 h-2.5 text-[#5e5e72]" />
                              <span className="text-[10px] text-[#5e5e72] truncate max-w-[200px]">{status.custom_url}</span>
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          {hasKey && (
                            <button
                              onClick={() => handleValidate(key)}
                              disabled={validating}
                              className="w-7 h-7 rounded-md flex items-center justify-center text-[#5e5e72] hover:text-[var(--venom-yellow)] hover:bg-[var(--venom-yellow)]/10 transition-colors disabled:opacity-50"
                              title="Validate key"
                            >
                              <RotateCw className={`w-3.5 h-3.5 ${validating ? 'animate-spin' : ''}`} />
                            </button>
                          )}
                          {hasKey && (
                            <button
                              onClick={() => handleRemove(key)}
                              className="w-7 h-7 rounded-md flex items-center justify-center text-[#5e5e72] hover:text-red-400 hover:bg-red-400/10 transition-colors"
                              title="Remove key"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => {
                              if (isEditing) {
                                setEditingProvider(null);
                                setApiKeyInput('');
                                setCustomUrlInput('');
                              } else {
                                setEditingProvider(key);
                                setApiKeyInput('');
                                setCustomUrlInput('');
                                setError('');
                                setSuccess('');
                              }
                            }}
                            className="px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors"
                            style={{
                              color: meta.color,
                              backgroundColor: `${meta.color}10`,
                            }}
                          >
                            {hasKey ? 'Update' : 'Add Key'}
                          </button>
                        </div>
                      </div>

                      {/* Inline edit form */}
                      {isEditing && (
                        <div className="px-4 pb-4 pt-1 border-t border-[#27272A]/50 space-y-2.5">
                          <div>
                            <label className="block text-[11px] text-[#9898a6] mb-1">API Key</label>
                            <input
                              type="password"
                              value={apiKeyInput}
                              onChange={e => { setApiKeyInput(e.target.value); setError(''); }}
                              onKeyDown={e => { if (e.key === 'Enter') handleSaveKey(); }}
                              placeholder={meta.placeholder}
                              autoFocus
                              className="w-full px-3 py-2 bg-[#1f1f24] border border-[#27272A] rounded-lg text-[13px] text-[#f2f2f3] placeholder:text-[#5e5e72] focus:outline-none focus:border-[var(--venom-yellow)]/40 transition-colors"
                            />
                          </div>

                          {/* Custom URL toggle */}
                          <button
                            onClick={() => toggleExpanded(key)}
                            className="flex items-center gap-1.5 text-[11px] text-[#5e5e72] hover:text-[#9898a6] transition-colors"
                          >
                            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                            <Globe className="w-3 h-3" />
                            Custom API URL
                          </button>

                          {isExpanded && (
                            <div>
                              <label className="block text-[11px] text-[#9898a6] mb-1">Custom Base URL</label>
                              <input
                                type="text"
                                value={customUrlInput}
                                onChange={e => setCustomUrlInput(e.target.value)}
                                placeholder={`https://api.${key}.com/v1`}
                                className="w-full px-3 py-2 bg-[#1f1f24] border border-[#27272A] rounded-lg text-[13px] text-[#f2f2f3] placeholder:text-[#5e5e72] focus:outline-none focus:border-[var(--venom-yellow)]/40 transition-colors"
                              />
                              <p className="text-[10px] text-[#5e5e72] mt-1">
                                For proxies, self-hosted endpoints, or alternative API bases.
                              </p>
                            </div>
                          )}

                          {error && (
                            <div className="flex items-center gap-1.5 text-[11px] text-red-400">
                              <AlertTriangle className="w-3 h-3 shrink-0" />
                              <span>{error}</span>
                            </div>
                          )}
                          {success && (
                            <div className="flex items-center gap-1.5 text-[11px] text-green-400">
                              <Check className="w-3 h-3 shrink-0" />
                              <span>{success}</span>
                            </div>
                          )}

                          <div className="flex items-center justify-between pt-1">
                            <a
                              href={meta.docsUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-[10px] text-[#5e5e72] hover:text-[#9898a6] transition-colors"
                            >
                              Get API key <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => { setEditingProvider(null); setApiKeyInput(''); setCustomUrlInput(''); }}
                                className="px-2.5 py-1 text-[11px] text-[#9898a6] hover:text-[#f2f2f3] rounded-md hover:bg-[#27272A] transition-colors"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={handleSaveKey}
                                disabled={saving || !apiKeyInput.trim()}
                                className="flex items-center gap-1.5 px-3 py-1 bg-[var(--venom-yellow)] text-black text-[11px] font-medium rounded-md hover:brightness-110 transition-all disabled:opacity-40"
                              >
                                {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Shield className="w-3 h-3" />}
                                {saving ? 'Saving...' : 'Save & Validate'}
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Model Provider Routing */}
              <div className="px-5 pt-5 pb-2">
                <p className="text-[11px] font-semibold tracking-[0.06em] uppercase text-[#5e5e72] mb-1">
                  Model Routing
                </p>
                <p className="text-[10px] text-[#5e5e72]/70 mb-3">
                  Choose which provider to use for each BYOK model.
                </p>
              </div>

              <div className="px-5 pb-5">
                <div className="border border-[#27272A] rounded-xl overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-[#27272A]">
                        <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#5e5e72]">Model</th>
                        <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#5e5e72]">Provider</th>
                      </tr>
                    </thead>
                    <tbody>
                      {models.map(model => (
                        <tr key={model.model_id} className="border-b border-[#27272A]/50 last:border-b-0">
                          <td className="px-4 py-2.5">
                            <span className="text-[12px] text-[#f2f2f3] font-medium">
                              {MODEL_DISPLAY_NAMES[model.model_id] || model.model_id}
                            </span>
                          </td>
                          <td className="px-4 py-2.5">
                            <select
                              value={model.provider}
                              onChange={e => handleModelProviderChange(model.model_id, e.target.value)}
                              className="bg-[#1f1f24] border border-[#27272A] rounded-md px-2 py-1 text-[11px] text-[#f2f2f3] focus:outline-none focus:border-[var(--venom-yellow)]/40 transition-colors cursor-pointer"
                            >
                              {model.providers.map(p => (
                                <option key={p} value={p}>
                                  {PROVIDERS[p]?.name || p}
                                </option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#27272A] shrink-0">
          <div className="flex items-center gap-1.5">
            <Shield className="w-3 h-3 text-[#5e5e72]" />
            <p className="text-[10px] text-[#5e5e72]">
              Keys are encrypted with AES-256 and stored in your database. Never shared with third parties.
            </p>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
