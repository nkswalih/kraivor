import { useAuthStore } from '@/lib/stores/auth-store';
import type { SendMessagePayload, ChatMessage } from '@/types/domain/ai';

/* ─── AI Service Base URL ────────────────────────────────── */

const AI_BASE = '/api/ai';

/* ─── Frontend model ID → Backend model ID mapping ──────── */

const MODEL_MAP: Record<string, string> = {
  // Kraivor
  'krait-2.0': 'openrouter/auto',
  // Groq (native API)
  'groq-qwen3-32b': 'qwen/qwen3-32b',
  'groq-qwen3.6-27b': 'qwen/qwen3.6-27b',
  // Free (OpenRouter)
  'cohere-north-mini-code': 'cohere/north-mini-code:free',
  'nvidia-nemotron-ultra': 'nvidia/nemotron-3-ultra-550b-a55b:free',
  'tencent-hy3': 'tencent/hy3:free',
  'poolside-laguna-xs': 'poolside/laguna-xs-2.1:free',
  'poolside-laguna-m': 'poolside/laguna-m.1:free',
  'nvidia-nemotron-super': 'nvidia/nemotron-3-super-120b-a12b:free',
  'google-gemma-4': 'google/gemma-4-31b-it:free',
  'nvidia-nemotron-nano': 'nvidia/nemotron-3-nano-30b-a3b:free',
  'openai-gpt-oss': 'openai/gpt-oss-120b:free',
  // BYOK - Anthropic
  'claude-fable-5': 'anthropic/claude-fable-5',
  'claude-opus-4-8': 'anthropic/claude-opus-4-8',
  'claude-opus-4-7': 'anthropic/claude-opus-4-7',
  'claude-sonnet-5': 'anthropic/claude-sonnet-5',
  'claude-sonnet-4-6': 'anthropic/claude-sonnet-4-6',
  // BYOK - OpenAI
  'gpt-5.6-sol': 'openai/gpt-5.6-sol',
  'gpt-5.6-terra': 'openai/gpt-5.6-terra',
  'gpt-5.5': 'openai/gpt-5.5',
  'gpt-5.4': 'openai/gpt-5.4',
  // BYOK - Google
  'gemini-3.5-flash': 'google/gemini-3.5-flash',
  'gemini-3.1-pro': 'google/gemini-3.1-pro',
  // BYOK - DeepSeek
  'deepseek-v4-pro': 'deepseek/deepseek-v4-pro',
  // BYOK - xAI
  'grok-4.3': 'xai/grok-4.3',
};

export function resolveModelId(frontendId: string): string {
  return MODEL_MAP[frontendId] ?? frontendId;
}

/* ─── Model listing types ────────────────────────────────── */

export type ModelTier = 'kraivor' | 'groq' | 'free' | 'byok';

export interface ModelItem {
  id: string;
  name: string;
  tier: ModelTier;
  provider: string;
  backendModel: string;
  latency?: string;
  context?: string;
  icon?: string;
}

/* ─── BYOK types ──────────────────────────────────────────── */

export type ByokProvider = 'openrouter' | 'anthropic' | 'openai' | 'google' | 'deepseek' | 'xai' | 'groq';

export interface ByokKeyStatus {
  hasKey: boolean;
  provider: ByokProvider;
  modelCount: number;
}

/* ─── Auth helper ────────────────────────────────────────── */

function getJwt(): string | null {
  if (typeof window === 'undefined') return null;
  return useAuthStore.getState().accessToken;
}

/* ─── Error ──────────────────────────────────────────────── */

export class AiApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'AiApiError';
  }
}

/* ─── API Client ─────────────────────────────────────────── */

export interface EnrichFindingItem {
  title: string;
  category: string;
  severity: string;
  description: string;
  recommendation: string;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  code_snippet: string;
}

export interface EnrichRequest {
  findings: EnrichFindingItem[];
  overall_score?: number | null;
  tier?: string | null;
  languages?: string[] | null;
  frameworks?: string[] | null;
}

export interface EnrichedFindingItem extends EnrichFindingItem {
  ai_explanation: string;
  ai_recommendation: string;
  is_ai_enriched: boolean;
}

export interface EnrichResponse {
  findings: EnrichedFindingItem[];
  ai_executive_summary: string;
}

export interface ProvisionResponse {
  provider: string;
  model_access: string[];
  rate_limit: Record<string, unknown>;
  provisioned_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  model: string | null;
  message_count: number;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface HistoryMessage {
  id: string;
  role: string;
  content: string;
  model: string | null;
  created_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}

export interface MessageListResponse {
  messages: HistoryMessage[];
  conversation_id: string;
  total: number;
}

export const aiApi = {
  async enrichAnalysis(request: EnrichRequest): Promise<EnrichResponse> {
    return aiPost<EnrichResponse>('/v1/analysis/enrich', request);
  },

  async provisionApiKey(provider: string, _apiKey?: string): Promise<ProvisionResponse> {
    return aiPost<ProvisionResponse>('/v1/api-keys/provision', { provider, tier: 'free' });
  },

  async listConversations(workspaceId?: string): Promise<ConversationListResponse> {
    const params = new URLSearchParams({ limit: '50' });
    if (workspaceId) params.set('workspace_id', workspaceId);
    return aiFetch<ConversationListResponse>(`/v1/conversations?${params}`);
  },

  async getMessages(conversationId: string): Promise<MessageListResponse> {
    return aiFetch<MessageListResponse>(`/v1/conversations/${conversationId}/messages?limit=500`);
  },

  /* ─── Dynamic model listing ─────────────────────────────── */

  async listModels(): Promise<ModelItem[]> {
    const res = await aiFetch<{ models: ModelItem[]; default: string }>('/v1/models');
    return res.models || [];
  },

  /* ─── BYOK key management ──────────────────────────────── */

  async submitByokKey(provider: ByokProvider, apiKey: string): Promise<{ ok: boolean }> {
    return aiPost('/v1/byok/submit', { provider, api_key: apiKey });
  },

  async getByokStatus(): Promise<{ providers: Record<string, boolean> }> {
    return aiFetch<{ providers: Record<string, boolean> }>('/v1/byok/status');
  },

  async removeByokKey(provider: ByokProvider): Promise<{ ok: boolean }> {
    return aiFetch(`/v1/byok/${provider}`, { method: 'DELETE' } as RequestInit);
  },

  /* ─── Send message ─────────────────────────────────────── */

  async sendMessage(payload: SendMessagePayload): Promise<ChatMessage> {
    const model = payload.model ? resolveModelId(payload.model) : undefined;
    return aiPost<ChatMessage>('/v1/chat', {
      message: payload.content,
      conversation_id: payload.sessionId,
      workspace_id: useAuthStore.getState().workspaceId,
      stream: false,
      model,
    });
  },

  async updateConversation(
    conversationId: string,
    data: { title?: string; is_pinned?: boolean },
  ): Promise<ConversationSummary> {
    return aiPatch<ConversationSummary>(`/v1/conversations/${conversationId}`, data);
  },

  async *streamMessage(payload: SendMessagePayload, signal?: AbortSignal) {
    const model = payload.model ? resolveModelId(payload.model) : undefined;
    const workspaceId = useAuthStore.getState().workspaceId;

    const response = await fetch(`${AI_BASE}/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(getJwt() ? { Authorization: `Bearer ${getJwt()}` } : {}),
      },
      body: JSON.stringify({
        message: payload.content,
        conversation_id: payload.sessionId,
        workspace_id: workspaceId,
        repo_ids: payload.repo_ids,
        stream: true,
        model,
      }),
      signal,
    });

    if (response.status === 429) {
      throw new AiApiError(429, 'rate_limited', 'Rate limit reached. Upgrade for more.');
    }

    if (!response.ok) {
      throw new AiApiError(response.status, 'stream_failed', 'Stream failed');
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          try {
            const parsed = JSON.parse(data);
            yield parsed;
          } catch {
            yield data;
          }
        }
      }
    }
  },


};

/* ─── Low-level fetch helpers ────────────────────────────── */

async function aiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${AI_BASE}${path}`;
  const token = getJwt();

  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers as Record<string, string>),
    },
  });

  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new AiApiError(
      res.status,
      body.error ?? body.code ?? 'unknown_error',
      body.message ?? body.detail ?? 'Request failed',
    );
  }
  return body as T;
}

async function aiPost<T>(path: string, body: unknown): Promise<T> {
  return aiFetch<T>(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

async function aiPatch<T>(path: string, body: unknown): Promise<T> {
  return aiFetch<T>(path, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}
