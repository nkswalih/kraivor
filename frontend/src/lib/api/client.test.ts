import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AxiosError } from 'axios';
import type { AxiosAdapter, AxiosResponse } from 'axios';

/**
 * Auth-token behaviour of the shared axios client.
 *
 * This is the highest-risk frontend path: it decides whether a bearer token is
 * attached to a request, and whether a 401 triggers a refresh-and-retry or a
 * hard sign-out. A regression here either leaks a token to a public endpoint or
 * leaves the user stuck in an unrecoverable session.
 *
 * These tests drive the real interceptor chain by swapping the axios *adapter*
 * (the lowest layer). Mocking `client.get` would bypass the interceptors
 * entirely and prove nothing.
 */

const authStore = {
  accessToken: 'valid-access-token' as string | null,
  clearAuth: vi.fn(),
  setState: vi.fn((partial: Record<string, unknown>) => {
    if ('accessToken' in partial) {
      authStore.accessToken = partial.accessToken as string;
    }
  }),
  getState: () => ({
    accessToken: authStore.accessToken,
    clearAuth: authStore.clearAuth,
  }),
};

vi.mock('@/lib/stores/auth-store', () => ({ useAuthStore: authStore }));

vi.mock('@/config', () => ({
  config: { api: { baseUrl: 'http://localhost:8001', timeout: 30000 } },
}));

const { apiClient } = await import('@/lib/api/client');
const instance = (apiClient as unknown as { client: { defaults: { adapter: AxiosAdapter } } })
  .client;

/** Every request the adapter saw, in order. */
let seen: Array<{ url?: string; method?: string; auth?: string | null }> = [];

function respondWith(handler: (url: string) => AxiosResponse | Promise<AxiosResponse>) {
  // The adapter receives axios's internal config type, which is not exported
  // in a usable form; narrow it to the fields this test actually reads.
  type AdapterConfig = Parameters<AxiosAdapter>[0];

  instance.defaults.adapter = (async (rawConfig) => {
    const config = rawConfig as AdapterConfig;
    seen.push({
      url: config.url,
      method: config.method,
      // axios types header values loosely; this test only cares that the
      // bearer token is present, so normalise to string here.
      auth: String(config.headers?.Authorization ?? ''),
    });
    const result = await handler(config.url ?? '');
    const response = {
      data: result.data,
      status: result.status,
      statusText: 'OK',
      headers: {},
      config,
    } as AxiosResponse;

    // A real adapter applies `validateStatus` (reject outside 2xx) — a custom
    // adapter is responsible for that itself, otherwise the response
    // interceptor chain never sees an error at all.
    const validate = config.validateStatus ?? ((s: number) => s >= 200 && s < 300);
    if (!validate(result.status)) {
      throw new AxiosError(
        `Request failed with status code ${result.status}`,
        result.status >= 500 ? 'ERR_BAD_RESPONSE' : 'ERR_BAD_REQUEST',
        config as never,
        undefined,
        response
      );
    }
    return response;
  }) as AxiosAdapter;
}

const ok = (data: unknown) => ({ data, status: 200 }) as AxiosResponse;

describe('apiClient auth interceptor', () => {
  beforeEach(() => {
    seen = [];
    authStore.accessToken = 'valid-access-token';
    authStore.clearAuth.mockClear();
    authStore.setState.mockClear();
  });

  it('attaches the bearer token to a normal API call', async () => {
    respondWith(() => ok({ name: 'ws' }));

    await apiClient.get('/api/workspaces/');

    expect(seen).toHaveLength(1);
    expect(seen[0].auth).toBe('Bearer valid-access-token');
  });

  it('does NOT attach the bearer token to a public auth endpoint', async () => {
    respondWith(() => ok({}));

    await apiClient.post('/auth/signin/password/', { password: 'x' });

    expect(seen[0].url).toBe('/auth/signin/password/');
    expect(seen[0].auth).toBe('');
  });

  it('refreshes the token and retries once on 401', async () => {
    let protectedCalls = 0;
    respondWith(url => {
      if (url === '/auth/refresh/') {
        return ok({ access_token: 'refreshed-token' });
      }
      if (url === '/api/protected/') {
        protectedCalls += 1;
        // 401 the first time, succeed on the retry with the new token.
        return protectedCalls === 1
          ? ({ data: { detail: 'nope' }, status: 401 } as AxiosResponse)
          : ok({ ok: true });
      }
      return ok({});
    });

    const result = await apiClient.get('/api/protected/');

    expect(result).toEqual({ ok: true });
    // original call, refresh call, retry
    expect(seen.map(s => s.url)).toEqual([
      '/api/protected/',
      '/auth/refresh/',
      '/api/protected/',
    ]);
    expect(seen[2].auth).toBe('Bearer refreshed-token');
    expect(authStore.setState).toHaveBeenCalledWith({ accessToken: 'refreshed-token' });
    expect(authStore.clearAuth).not.toHaveBeenCalled();
  });

  it('signs the user out when the refresh itself fails', async () => {
    respondWith(url => {
      if (url === '/api/protected/') {
        return { data: {}, status: 401 } as AxiosResponse;
      }
      // refresh fails
      return Promise.reject(new Error('refresh failed'));
    });

    await expect(apiClient.get('/api/protected/')).rejects.toBeDefined();

    expect(authStore.clearAuth).toHaveBeenCalled();
    expect(authStore.setState).not.toHaveBeenCalled();
  });

  it('does not attempt a refresh for a public auth endpoint 401', async () => {
    respondWith(() => ({ data: {}, status: 401 }) as AxiosResponse);

    await expect(apiClient.post('/auth/signin/password/', {})).rejects.toBeDefined();

    // Only the original call — no refresh attempt, no sign-out.
    expect(seen).toHaveLength(1);
    expect(authStore.clearAuth).not.toHaveBeenCalled();
  });

  it('passes non-401 errors straight through', async () => {
    respondWith(() => ({ data: { detail: 'boom' }, status: 500 }) as AxiosResponse);

    await expect(apiClient.get('/api/boom/')).rejects.toBeDefined();

    expect(seen).toHaveLength(1);
    expect(authStore.clearAuth).not.toHaveBeenCalled();
  });
});
