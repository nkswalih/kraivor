import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { config } from '@/config';
import { API_ENDPOINTS } from '@/constants';
import type { ApiError, QueueItem } from '@/types/api';
import { useAuthStore } from '@/lib/stores/auth-store';

let isRefreshing = false;
let failedQueue: QueueItem[] = [];

const processQueue = (error: AxiosError | null, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const PUBLIC_AUTH_EXACT_PATHS = [
  '/auth/signin/password/',
  '/auth/signin/identify/',
  '/auth/signup/',
  '/auth/refresh/',
  '/auth/forgot-password/',
  '/auth/reset-password/',
  '/auth/verify-email/',
  '/auth/resend-verification/',
];

const PUBLIC_AUTH_PREFIXES = ['/auth/signin/otp/', '/auth/otp/', '/auth/oauth/'];

const normalizeApiPath = (url: string | undefined): string => {
  if (!url) return '';
  try {
    return new URL(url, config.api.baseUrl).pathname;
  } catch {
    return url.split('?')[0] ?? '';
  }
};

const isPublicAuthEndpoint = (url: string | undefined): boolean => {
  const pathname = normalizeApiPath(url);
  const normalizedPathname = pathname.endsWith('/') ? pathname : `${pathname}/`;
  return (
    PUBLIC_AUTH_EXACT_PATHS.includes(normalizedPathname) ||
    PUBLIC_AUTH_PREFIXES.some(prefix => normalizedPathname.startsWith(prefix))
  );
};

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = this.createClient();
    this.setupInterceptors();
  }

  private createClient(): AxiosInstance {
    return axios.create({
      baseURL: config.api.baseUrl,
      timeout: config.api.timeout,
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true,
    });
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (isPublicAuthEndpoint(config.url)) {
          delete config.headers.Authorization;
          return config;
        }
        const token = useAuthStore.getState().accessToken;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      error => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      response => response,
      async (error: AxiosError<ApiError>) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
        if (!originalRequest) return Promise.reject(error);

        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          !isPublicAuthEndpoint(originalRequest.url)
        ) {
          if (isRefreshing) {
            return new Promise((resolve, reject) => {
              failedQueue.push({ resolve, reject, config: originalRequest });
            }).then(token => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.client(originalRequest);
            });
          }

          originalRequest._retry = true;
          isRefreshing = true;

          try {
            const response = await this.client.post(API_ENDPOINTS.AUTH.REFRESH);
            const newToken: string = response.data.access_token || response.data.accessToken || '';
            useAuthStore.setState({ accessToken: newToken });
            processQueue(null, newToken);
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            processQueue(refreshError as AxiosError, null);
            useAuthStore.getState().clearAuth();
            return Promise.reject(refreshError);
          } finally {
            isRefreshing = false;
          }
        }
        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: Record<string, unknown>) {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: unknown, config?: Record<string, unknown>) {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: unknown, config?: Record<string, unknown>) {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: unknown, config?: Record<string, unknown>) {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: Record<string, unknown>) {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  async request<T>(config: {
    url: string;
    method: string;
    data?: unknown;
    params?: Record<string, unknown>;
  }) {
    const response = await this.client.request<T>(config);
    return response.data;
  }
}

export const apiClient = new ApiClient();
export default apiClient;

/* ─── CORE BACKEND API (native fetch, no axios) ──────────────────── */

class CoreApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = 'CoreApiError';
  }
}

function getJwt(): string | null {
  if (typeof window === 'undefined') return null;
  return useAuthStore.getState().accessToken;
}

/* Token refresh with dedup — multiple 401s queue behind a single refresh call */
let coreRefreshing = false;
let coreRefreshPromise: Promise<string | null> | null = null;

async function tryRefreshToken(): Promise<string | null> {
  if (coreRefreshing && coreRefreshPromise) return coreRefreshPromise;
  coreRefreshing = true;
  const base = process.env.NEXT_PUBLIC_API_URL ?? '/api';
  coreRefreshPromise = (async () => {
    try {
      const r = await fetch(`${base}/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (!r.ok) return null;
      const data = await r.json();
      const t = data.access_token ?? data.accessToken ?? null;
      if (t) useAuthStore.setState({ accessToken: t });
      return t;
    } catch {
      return null;
    } finally {
      coreRefreshing = false;
      coreRefreshPromise = null;
    }
  })();
  return coreRefreshPromise;
}

const REQUEST_TIMEOUT = 15_000;

async function coreRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? '/api';
  const token = getJwt();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  const fetchOptions = (overrides: RequestInit = {}): RequestInit => ({
    ...init,
    ...overrides,
    signal: overrides.signal ?? controller.signal,
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
      ...overrides.headers,
    },
  });

  const doFetch = (opts: RequestInit = {}) => fetch(`${base}${path}`, fetchOptions(opts));

  try {
    let res = await doFetch();

    /* ── On 401, try to refresh the token and retry once ── */
    if (res.status === 401) {
      const newToken = await tryRefreshToken();
      if (newToken) {
        res = await doFetch({ headers: { Authorization: `Bearer ${newToken}` } as Record<string, string> });
      }
    }

    if (res.status === 401) {
      useAuthStore.getState().clearAuth();
      throw new CoreApiError(401, 'token_expired', 'Session expired');
    }

    if (res.status === 204) return undefined as T;

    const body = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new CoreApiError(
        res.status,
        body.error ?? body.code ?? 'unknown_error',
        body.message ?? body.detail ?? 'Request failed'
      );
    }

    return body as T;
  } finally {
    clearTimeout(timeout);
  }
}

export { coreRequest };

export const coreApi = {
  get: <T>(path: string, init?: RequestInit) => coreRequest<T>(path, { method: 'GET', ...init }),
  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    coreRequest<T>(path, {
      method: 'POST',
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),
  patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
    coreRequest<T>(path, {
      method: 'PATCH',
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),
  put: <T>(path: string, body?: unknown, init?: RequestInit) =>
    coreRequest<T>(path, {
      method: 'PUT',
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),
  delete: <T>(path: string, init?: RequestInit) =>
    coreRequest<T>(path, { method: 'DELETE', ...init }),
};

/* ─── IDENTITY SERVICE API (same gateway, separate export) ─────── */
export const identityRequest = coreRequest;

export const identityApi = {
  get: <T>(path: string, init?: RequestInit) => coreRequest<T>(path, { method: 'GET', ...init }),
  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    coreRequest<T>(path, {
      method: 'POST',
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),
  patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
    coreRequest<T>(path, {
      method: 'PATCH',
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),
  put: <T>(path: string, body?: unknown, init?: RequestInit) =>
    coreRequest<T>(path, {
      method: 'PUT',
      body: body != null ? JSON.stringify(body) : undefined,
      ...init,
    }),
  delete: <T>(path: string, init?: RequestInit) =>
    coreRequest<T>(path, { method: 'DELETE', ...init }),
};
