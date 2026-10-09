/**
 * Canonical AI provider metadata.
 *
 * This table was previously copy-pasted into three components
 * (settings/ai-providers-view, ai/ai-byok-setup-dialog, ai/ai-byok-key-dialog)
 * and had already drifted: xAI was named "xAI" in two files and "xAI (Grok)"
 * in the third, and docsUrl was missing from one of them entirely.
 *
 * Add or edit a provider here only.
 */

export interface ProviderMeta {
  /** Display name, e.g. "Anthropic". */
  name: string;
  /** Masked example shown in the key input's placeholder. */
  placeholder: string;
  /** Brand accent colour. */
  color: string;
  /** Where users go to create a key. */
  docsUrl: string;
}

export const AI_PROVIDERS: Record<string, ProviderMeta> = {
  anthropic: {
    name: 'Anthropic',
    placeholder: 'sk-ant-api03-...',
    color: '#D97757',
    docsUrl: 'https://console.anthropic.com/settings/keys',
  },
  openai: {
    name: 'OpenAI',
    placeholder: 'sk-proj-...',
    color: '#10A37F',
    docsUrl: 'https://platform.openai.com/api-keys',
  },
  google: {
    name: 'Google AI',
    placeholder: 'AIza...',
    color: '#4285F4',
    docsUrl: 'https://aistudio.google.com/apikey',
  },
  deepseek: {
    name: 'DeepSeek',
    placeholder: 'sk-...',
    color: '#4D6BFE',
    docsUrl: 'https://platform.deepseek.com/api_keys',
  },
  xai: {
    name: 'xAI',
    placeholder: 'xai-...',
    color: '#FFFFFF',
    docsUrl: 'https://console.x.ai/',
  },
  groq: {
    name: 'Groq',
    placeholder: 'gsk_...',
    color: '#F55036',
    docsUrl: 'https://console.groq.com/keys',
  },
  openrouter: {
    name: 'OpenRouter',
    placeholder: 'sk-or-v1-...',
    color: '#8B5CF6',
    docsUrl: 'https://openrouter.ai/keys',
  },
};

/** Display order in the providers UI. */
export const AI_PROVIDER_ORDER = [
  'anthropic',
  'openai',
  'google',
  'groq',
  'deepseek',
  'xai',
  'openrouter',
] as const;

/** Fallback for an unknown provider id so the UI never renders "undefined". */
export const UNKNOWN_PROVIDER_META: ProviderMeta = {
  name: 'Unknown Provider',
  placeholder: 'API key',
  color: '#888888',
  docsUrl: '',
};

/** Look up a provider's metadata, falling back gracefully. */
export function getProviderMeta(provider: string): ProviderMeta {
  return AI_PROVIDERS[provider] ?? { ...UNKNOWN_PROVIDER_META, name: provider };
}
