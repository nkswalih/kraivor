'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Key,
  Check,
  X,
  Globe,
  Shield,
  RotateCw,
  ExternalLink,
  Loader2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
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

/* ─── Helpers ───────────────────────────────────────────── */

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

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

/* ─── Section Component ─────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="pb-6 border-b border-krait-border last:border-0">
      <h3 className="text-[11px] font-semibold tracking-[0.06em] uppercase text-text-tertiary mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

/* ─── Main Component ────────────────────────────────────── */

export function AiProvidersView() {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [models, setModels] = useState<ModelAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [customUrlInput, setCustomUrlInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [expandedUrls, setExpandedUrls] = useState<Set<string>>(new Set());

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
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save key');
    } finally {
      setSaving(false);
    }
  };

  /* ── Validate ──────────────────────────────────────────── */

  const handleValidate = async (provider: string) => {
    setValidating(provider);
    try {
      await jwtFetch(`/api/ai/v1/byok/providers/${provider}/validate`, { method: 'POST' });
      await loadData();
    } catch {
      // silent
    } finally {
      setValidating(null);
    }
  };

  /* ── Remove key ────────────────────────────────────────── */

  const handleRemove = async (provider: string) => {
    try {
      await jwtFetch(`/api/ai/v1/byok/providers/${provider}`, { method: 'DELETE' });
      await loadData();
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

  /* ── Render ────────────────────────────────────────────── */

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">AI Providers</h2>
        <p className="text-[12px] text-text-secondary mt-1">
          Manage API keys, provider routing, and custom endpoints for BYOK models.
        </p>
      </div>

      {/* ── Provider Keys ────────────────────────────────────── */}
      <Section title="Provider Keys">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-text-tertiary" />
          </div>
        ) : (
          <div className="space-y-1.5 max-w-[560px]">
            {PROVIDER_ORDER.map(key => {
              const meta = PROVIDERS[key];
              const status = providers.find(p => p.name === key);
              const hasKey = status?.has_key ?? false;
              const isEditing = editingProvider === key;

              return (
                <div key={key} className="border border-krait-border rounded-xl overflow-hidden">
                  {/* Provider row */}
                  <div className="flex items-center gap-3 px-4 py-3 bg-krait-surface-1">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                      style={{ backgroundColor: `${meta.color}15` }}
                    >
                      <Key className="w-4 h-4" style={{ color: meta.color }} strokeWidth={2} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-medium text-text-primary">{meta.name}</span>
                        {hasKey && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-[var(--color-success)]/10 text-[var(--color-success)] text-[10px] font-medium">
                            <Check className="w-2.5 h-2.5" /> Active
                          </span>
                        )}
                      </div>
                      {hasKey && (
                        <div className="flex items-center gap-3 mt-0.5">
                          {status?.custom_url && (
                            <div className="flex items-center gap-1">
                              <Globe className="w-2.5 h-2.5 text-text-tertiary" />
                              <span className="text-[10px] text-text-tertiary truncate max-w-[200px]">{status.custom_url}</span>
                            </div>
                          )}
                          <span className="text-[10px] text-text-tertiary">
                            Last validated: {timeAgo(status?.last_validated ?? null)}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {hasKey && (
                        <button
                          onClick={() => handleValidate(key)}
                          disabled={validating === key}
                          className="w-7 h-7 rounded-md flex items-center justify-center text-text-tertiary hover:text-[var(--venom-yellow)] hover:bg-[var(--venom-yellow)]/10 transition-colors disabled:opacity-50"
                          title="Validate key"
                        >
                          <RotateCw className={cn('w-3.5 h-3.5', validating === key && 'animate-spin')} />
                        </button>
                      )}
                      {hasKey && (
                        <button
                          onClick={() => handleRemove(key)}
                          className="w-7 h-7 rounded-md flex items-center justify-center text-text-tertiary hover:text-destructive hover:bg-destructive/10 transition-colors"
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
                            setError('');
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
                    <div className="px-4 pb-4 pt-3 border-t border-krait-border/50 space-y-2.5">
                      <div>
                        <label className="block text-[11px] font-medium text-text-secondary mb-1">API Key</label>
                        <input
                          type="password"
                          value={apiKeyInput}
                          onChange={e => { setApiKeyInput(e.target.value); setError(''); }}
                          onKeyDown={e => { if (e.key === 'Enter') handleSaveKey(); }}
                          placeholder={meta.placeholder}
                          autoFocus
                          className="w-full px-3 py-2 bg-krait-surface-1 border border-krait-border rounded-lg text-[13px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-primary/40 transition-colors"
                        />
                      </div>

                      {/* Custom URL toggle */}
                      <button
                        onClick={() => {
                          setExpandedUrls(prev => {
                            const next = new Set(prev);
                            if (next.has(key)) next.delete(key);
                            else next.add(key);
                            return next;
                          });
                        }}
                        className="flex items-center gap-1.5 text-[11px] text-text-tertiary hover:text-text-secondary transition-colors"
                      >
                        {expandedUrls.has(key) ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                        <Globe className="w-3 h-3" />
                        Custom API URL
                      </button>

                      {expandedUrls.has(key) && (
                        <div>
                          <label className="block text-[11px] font-medium text-text-secondary mb-1">Custom Base URL</label>
                          <input
                            type="text"
                            value={customUrlInput}
                            onChange={e => setCustomUrlInput(e.target.value)}
                            placeholder={`https://api.${key}.com/v1`}
                            className="w-full px-3 py-2 bg-krait-surface-1 border border-krait-border rounded-lg text-[13px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-primary/40 transition-colors"
                          />
                          <p className="text-[10px] text-text-tertiary mt-1">
                            For proxies, self-hosted endpoints, or alternative API bases.
                          </p>
                        </div>
                      )}

                      {error && (
                        <p className="text-[11px] text-destructive">{error}</p>
                      )}
                      {success && (
                        <p className="text-[11px] text-[var(--color-success)]">{success}</p>
                      )}

                      <div className="flex items-center justify-between pt-1">
                        <a
                          href={meta.docsUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-[10px] text-text-tertiary hover:text-text-secondary transition-colors"
                        >
                          Get API key <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => { setEditingProvider(null); setApiKeyInput(''); setCustomUrlInput(''); setError(''); }}
                            className="px-2.5 py-1 text-[11px] text-text-tertiary hover:text-text-primary rounded-md hover:bg-muted transition-colors"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSaveKey}
                            disabled={saving || !apiKeyInput.trim()}
                            className="flex items-center gap-1.5 px-3 py-1 bg-primary text-primary-foreground text-[11px] font-medium rounded-md hover:bg-primary-dark transition-all disabled:opacity-40"
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
        )}
      </Section>

      {/* ── Model Routing ────────────────────────────────────── */}
      <Section title="Model Routing">
        <p className="text-[12px] text-text-secondary mb-3">
          Choose which provider to use for each BYOK model. Models can route through native APIs or OpenRouter.
        </p>
        <div className="border border-krait-border rounded-xl overflow-hidden max-w-[560px]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-krait-border bg-krait-surface-1">
                <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-tertiary">Model</th>
                <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-tertiary">Provider</th>
              </tr>
            </thead>
            <tbody>
              {models.map(model => (
                <tr key={model.model_id} className="border-b border-krait-border/50 last:border-b-0">
                  <td className="px-4 py-2.5">
                    <span className="text-[12px] text-text-primary font-medium">
                      {MODEL_DISPLAY_NAMES[model.model_id] || model.model_id}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <select
                      value={model.provider}
                      onChange={e => handleModelProviderChange(model.model_id, e.target.value)}
                      className="bg-krait-surface-1 border border-krait-border rounded-md px-2 py-1 text-[11px] text-text-primary focus:outline-none focus:border-primary/40 transition-colors cursor-pointer"
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
      </Section>

      {/* ── Security Note ────────────────────────────────────── */}
      <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-krait-surface-1 border border-krait-border max-w-[560px]">
        <Shield className="w-4 h-4 text-text-tertiary shrink-0 mt-0.5" />
        <div>
          <p className="text-[12px] text-text-secondary">
            All API keys are encrypted with AES-256 and stored in your database row. They never leave Kraivor infrastructure and are only used to route requests to the selected provider.
          </p>
        </div>
      </div>
    </div>
  );
}
