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
