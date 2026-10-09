import { useAuthStore } from '@/lib/stores/auth-store';

const AI_BASE = '/api/ai';

function getJwt(): string | null {
  if (typeof window === 'undefined') return null;
  return useAuthStore.getState().accessToken;
}

export class KnowledgeAiApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = 'KnowledgeAiApiError';
  }
}

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
    throw new KnowledgeAiApiError(
      res.status,
      body.error ?? body.code ?? 'unknown_error',
      body.message ?? body.detail ?? 'Request failed',
    );
  }
  return body as T;
}

async function aiPost<T>(path: string, body: unknown): Promise<T> {
  return aiFetch<T>(path, { method: 'POST', body: JSON.stringify(body) });
}

/* ─── Types ───────────────────────────────────────────────── */

export interface HealthOverall {
  score: number;
  grade: string;
  breakdown: { coverage: number; freshness: number; quality: number; diversity: number };
}

export interface HealthReport {
  workspace_id: string;
  generated_at: string;
  overall_health: HealthOverall;
  stats: Record<string, unknown>;
  freshness: Record<string, unknown>;
  quality_distribution: Record<string, unknown>;
  provider_distribution: Array<{ provider: string; count: number }>;
  gaps: Array<{ topic: string; severity: string; recommendation: string }>;
  recommendations: string[];
}

export interface KnowledgeStats {
  workspace_id: string;
  total_items: number;
  unique_urls: number;
  providers: number;
  avg_trust: number;
  oldest: string | null;
  newest: string | null;
  source_types?: Record<string, number>;
  languages?: Record<string, number>;
}

export interface KnowledgeItem {
  id: string;
  source_url: string;
  source_provider: string;
  title: string | null;
  content_preview: string;
  fetched_at: string | null;
  created_at: string | null;
  source_type: string | null;
  original_filename: string | null;
  language: string | null;
}

export interface GraphStats {
  workspace_id: string;
  entities: number;
  entity_types: number;
  relationships: number;
  relationship_types: number;
}

export interface GraphEntity {
  name: string;
  type: string;
  mentions: number;
  first_seen: string | null;
  last_seen: string | null;
}

export interface QueryStats {
  workspace_id: string;
  total_queries: number;
  cache_hits: number;
  cache_hit_rate: number;
  errors: number;
  error_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  max_latency_ms: number;
  total_sources_fetched: number;
  period_hours: number;
}

export interface IngestFileResponse {
  success: boolean;
  source_type: string;
  title: string | null;
  total_characters: number;
  chunk_count: number;
  knowledge_ids: string[];
  language: string | null;
  metadata: Record<string, unknown>;
  error: string | null;
}

export interface WorkflowDefinition {
  name: string;
  description: string;
  category: string;
  tags: string[];
  step_count: number;
  steps: Array<{ id: string; name: string; depends_on: string[] }>;
}

export interface WorkflowRunResult {
  workflow_id: string;
  workflow_name: string;
  status: string;
  step_results: Record<string, { step_id: string; status: string; output: Record<string, unknown>; error: string | null; duration_ms: number }>;
  outputs: Record<string, unknown>;
  total_duration_ms: number;
  error: string | null;
}

export interface TemplateSummary {
  template_id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  item_count: number;
  author: string;
}

/* ─── API Methods ─────────────────────────────────────────── */

export const knowledgeAiApi = {
  // Health
  getHealth: (workspaceId: string) =>
    aiFetch<HealthReport>(`/v1/knowledge/health/${workspaceId}`),

  // Stats
  getStats: (workspaceId: string) =>
    aiFetch<KnowledgeStats>(`/v1/knowledge/stats/${workspaceId}`),

  // List items
  listItems: (workspaceId: string, limit = 20, offset = 0, sourceType?: string) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (sourceType) params.set('source_type', sourceType);
    return aiFetch<{ workspace_id: string; items: KnowledgeItem[]; total: number }>(
      `/v1/knowledge/list/${workspaceId}?${params}`
    );
  },

  // Search
  search: (workspaceId: string, query: string, topK = 10) =>
    aiPost<{ query: string; results: Array<{ source: string; title: string; content: string; similarity: number }>; total: number }>(
      '/v1/knowledge/search/advanced',
      { workspace_id: workspaceId, query, top_k: topK }
    ),

  // Graph
  getGraphStats: (workspaceId: string) =>
    aiFetch<GraphStats>(`/v1/knowledge/graph/stats/${workspaceId}`),

  getGraphEntities: (workspaceId: string, topN = 20) =>
    aiFetch<GraphEntity[]>(`/v1/knowledge/graph/entities/${workspaceId}?top_n=${topN}`),

  // Monitoring
  getQueryStats: (workspaceId: string, hours = 24) =>
    aiFetch<QueryStats>(`/v1/knowledge/monitoring/stats/${workspaceId}?hours=${hours}`),

  // Ingest file
  ingestFile: async (workspaceId: string, file: File, language?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('workspace_id', workspaceId);
    if (language) formData.append('language', language);

    const token = getJwt();
    const res = await fetch(`${AI_BASE}/v1/knowledge/ingest/file?workspace_id=${workspaceId}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) throw new KnowledgeAiApiError(res.status, 'ingest_failed', 'File ingestion failed');
    return res.json() as Promise<IngestFileResponse>;
  },

  // Ingest text
  ingestText: (workspaceId: string, text: string, title?: string) =>
    aiPost<IngestFileResponse>('/v1/knowledge/ingest/text', {
      workspace_id: workspaceId,
      text,
      title,
    }),

  // Workflows
  getWorkflowDefinitions: () =>
    aiFetch<WorkflowDefinition[]>('/v1/knowledge/workflows/definitions'),

  runWorkflow: (workspaceId: string, workflowName: string, topic?: string) =>
    aiPost<WorkflowRunResult>('/v1/knowledge/workflows/run', {
      workspace_id: workspaceId,
      workflow_name: workflowName,
      topic,
    }),

  // Templates
  getTemplates: () =>
    aiFetch<{ templates: TemplateSummary[] }>('/v1/knowledge/marketplace/templates'),

  importTemplate: (workspaceId: string, templateId: string) =>
    aiPost<{ success: boolean; items_imported: number }>(
      '/v1/knowledge/marketplace/templates/import',
      { workspace_id: workspaceId, template_id: templateId }
    ),

  // Export bundle
  exportBundle: (workspaceId: string, name?: string) =>
    aiPost<{ bundle_id: string; bundle_json: string; item_count: number }>(
      '/v1/knowledge/marketplace/export',
      { workspace_id: workspaceId, name }
    ),
};
