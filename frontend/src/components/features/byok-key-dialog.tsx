'use client';

import { createPortal } from 'react-dom';
import { useState, useRef, useEffect } from 'react';
import { Key, X, Check, AlertTriangle, Loader2 } from 'lucide-react';
import { aiApi, type ByokProvider } from '@/lib/api/ai-api';

const PROVIDER_META: Record<string, { name: string; placeholder: string; color: string }> = {
  anthropic: { name: 'Anthropic', placeholder: 'sk-ant-api03-...', color: '#D97757' },
  openai: { name: 'OpenAI', placeholder: 'sk-proj-...', color: '#10A37F' },
  google: { name: 'Google AI', placeholder: 'AIza...', color: '#4285F4' },
  deepseek: { name: 'DeepSeek', placeholder: 'sk-...', color: '#4D6BFE' },
  xai: { name: 'xAI (Grok)', placeholder: 'xai-...', color: '#FFFFFF' },
  groq: { name: 'Groq', placeholder: 'gsk_...', color: '#F55036' },
  openrouter: { name: 'OpenRouter', placeholder: 'sk-or-v1-...', color: '#8B5CF6' },
};

interface ByokKeyDialogProps {
  provider: string;
  onClose: () => void;
  onSave: () => void;
}

export function ByokKeyDialog({ provider, onClose, onSave }: ByokKeyDialogProps) {
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const meta = PROVIDER_META[provider] || { name: provider, placeholder: 'API key', color: '#888' };

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleSave = async () => {
    if (!apiKey.trim()) {
      setError('Please enter an API key');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await aiApi.submitByokKey(provider as ByokProvider, apiKey.trim());
      setSuccess(true);
      setTimeout(() => {
        onSave();
        onClose();
      }, 600);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to save key';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[2147483647] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Dialog */}
      <div
        className="relative w-full max-w-[400px] mx-4 bg-[#141416] border border-[#27272A] rounded-2xl shadow-2xl overflow-hidden"
        onPointerDown={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: `${meta.color}15` }}
            >
              <Key className="w-4 h-4" style={{ color: meta.color }} strokeWidth={2} />
            </div>
            <div>
              <h3 className="text-[14px] font-semibold text-[#f2f2f3]">{meta.name} API Key</h3>
              <p className="text-[11px] text-[#5e5e72] mt-0.5">BYOK — use your own key</p>
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
        <div className="px-5 pb-5">
          <label className="block text-[12px] text-[#9898a6] mb-1.5">API Key</label>
          <input
            ref={inputRef}
            type="password"
            value={apiKey}
            onChange={e => { setApiKey(e.target.value); setError(''); }}
            onKeyDown={e => { if (e.key === 'Enter') handleSave(); }}
            placeholder={meta.placeholder}
            className="w-full px-3 py-2 bg-[#1f1f24] border border-[#27272A] rounded-lg text-[13px] text-[#f2f2f3] placeholder:text-[#5e5e72] focus:outline-none focus:border-[var(--venom-yellow)]/40 transition-colors"
          />

          {error && (
            <div className="flex items-center gap-1.5 mt-2 text-[12px] text-red-400">
              <AlertTriangle className="w-3 h-3 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-1.5 mt-2 text-[12px] text-green-400">
              <Check className="w-3 h-3 shrink-0" />
              <span>Key saved successfully</span>
            </div>
          )}

          <p className="text-[11px] text-[#5e5e72] mt-3 leading-relaxed">
            Your key is encrypted and stored securely. It never leaves Kraivor infrastructure
            and is only used to route requests to {meta.name}.
          </p>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 mt-4">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-[12px] text-[#9898a6] hover:text-[#f2f2f3] rounded-md hover:bg-[#27272A] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || success}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-[var(--venom-yellow)] text-black text-[12px] font-medium rounded-md hover:brightness-110 transition-all disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : success ? (
                <Check className="w-3 h-3" />
              ) : null}
              {success ? 'Saved' : 'Save Key'}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

/* ─── API Keys Management Panel (opened from settings) ──── */

interface ApiKeysPanelProps {
  onClose: () => void;
  onEdit: (provider: string) => void;
}

export function ApiKeysPanel({ onClose, onEdit }: ApiKeysPanelProps) {
  const [statuses, setStatuses] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState<string | null>(null);

  const loadStatuses = async () => {
    setLoading(true);
    try {
      const res = await aiApi.getByokStatus();
      setStatuses(res.providers || {});
    } catch {
      setStatuses({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatuses();
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleRemove = async (provider: string) => {
    setRemoving(provider);
    try {
      await aiApi.removeByokKey(provider as ByokProvider);
      await loadStatuses();
    } catch {
      // ignore
    } finally {
      setRemoving(null);
    }
  };

  const providers = Object.entries(PROVIDER_META);

  return createPortal(
    <div className="fixed inset-0 z-[2147483647] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      <div
        className="relative w-full max-w-[420px] mx-4 bg-[#141416] border border-[#27272A] rounded-2xl shadow-2xl overflow-hidden"
        onPointerDown={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-[#27272A]">
          <div className="flex items-center gap-2.5">
            <Key className="w-4 h-4 text-[var(--venom-yellow)]" strokeWidth={2} />
            <h3 className="text-[14px] font-semibold text-[#f2f2f3]">API Keys</h3>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-md flex items-center justify-center text-[#5e5e72] hover:text-[#f2f2f3] hover:bg-[#27272A] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Provider list */}
        <div className="max-h-[400px] overflow-y-auto">
          {loading ? (
            <div className="px-5 py-8 flex items-center justify-center">
              <Loader2 className="w-4 h-4 text-[#5e5e72] animate-spin" />
            </div>
          ) : (
            providers.map(([key, meta]) => {
              const hasKey = statuses[key] === true;
              return (
                <div
                  key={key}
                  className="flex items-center justify-between px-5 py-3 border-b border-[#27272A]/50 last:border-b-0 hover:bg-[#1f1f24] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-7 h-7 rounded-md flex items-center justify-center"
                      style={{ backgroundColor: `${meta.color}15` }}
                    >
                      <Key className="w-3.5 h-3.5" style={{ color: meta.color }} strokeWidth={2} />
                    </div>
                    <div>
                      <span className="text-[13px] text-[#f2f2f3] font-medium">{meta.name}</span>
                      <div className="text-[11px] text-[#5e5e72]">
                        {hasKey ? 'Key configured' : 'No key'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {hasKey && (
                      <button
                        onClick={() => handleRemove(key)}
                        disabled={removing === key}
                        className="px-2.5 py-1 text-[11px] text-red-400 hover:bg-red-400/10 rounded-md transition-colors disabled:opacity-50"
                      >
                        {removing === key ? 'Removing...' : 'Remove'}
                      </button>
                    )}
                    <button
                      onClick={() => onEdit(key)}
                      className="px-2.5 py-1 text-[11px] text-[var(--venom-yellow)] hover:bg-[var(--venom-yellow)]/10 rounded-md transition-colors"
                    >
                      {hasKey ? 'Update' : 'Add Key'}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#27272A]">
          <p className="text-[11px] text-[#5e5e72] leading-relaxed">
            BYOK keys are encrypted with AES-256 and stored in your database row.
            They are only used to route requests to the selected provider.
          </p>
        </div>
      </div>
    </div>,
    document.body,
  );
}
