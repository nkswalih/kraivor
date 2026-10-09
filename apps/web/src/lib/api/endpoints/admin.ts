import { useAuthStore } from '@/lib/stores/auth-store';

function getJwt(): string | null {
  if (typeof window === 'undefined') return null;
  return useAuthStore.getState().accessToken;
}

async function aiAdminRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `/api/ai${path}`;
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
    throw new Error(body.detail ?? body.message ?? `Request failed (${res.status})`);
  }
  return body as T;
}

export const adminEndpoints = {
  me: () => aiAdminRequest('/v1/admin/me'),

  // Providers
  listProviders: () => aiAdminRequest('/v1/admin/providers'),
  createProvider: (data: Record<string, unknown>) =>
    aiAdminRequest('/v1/admin/providers', { method: 'POST', body: JSON.stringify(data) }),
  updateProvider: (id: string, data: Record<string, unknown>) =>
    aiAdminRequest(`/v1/admin/providers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProvider: (id: string) =>
    aiAdminRequest(`/v1/admin/providers/${id}`, { method: 'DELETE' }),

  // Models
  listModels: () => aiAdminRequest('/v1/admin/models'),
  createModel: (data: Record<string, unknown>) =>
    aiAdminRequest('/v1/admin/models', { method: 'POST', body: JSON.stringify(data) }),
  updateModel: (id: string, data: Record<string, unknown>) =>
    aiAdminRequest(`/v1/admin/models/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteModel: (id: string) =>
    aiAdminRequest(`/v1/admin/models/${id}`, { method: 'DELETE' }),

  // Routes
  listRoutes: () => aiAdminRequest('/v1/admin/routes'),
  createRoute: (data: Record<string, unknown>) =>
    aiAdminRequest('/v1/admin/routes', { method: 'POST', body: JSON.stringify(data) }),
  updateRoute: (id: string, data: Record<string, unknown>) =>
    aiAdminRequest(`/v1/admin/routes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRoute: (id: string) =>
    aiAdminRequest(`/v1/admin/routes/${id}`, { method: 'DELETE' }),

  // Cache
  invalidateCache: () =>
    aiAdminRequest('/v1/admin/cache/invalidate', { method: 'POST' }),
};
