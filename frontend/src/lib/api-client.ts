import axios from 'axios';
import { useAuthStore } from '@/store/auth.store';
import { sileo } from 'sileo';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Skip refresh logic for auth endpoints to prevent infinite loops
    if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = 'Bearer ' + token;
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(`${API_URL}/auth/refresh/`, {}, { withCredentials: true });
        
        const { access } = response.data;
        useAuthStore.getState().setTokens(access);
        
        apiClient.defaults.headers.common.Authorization = `Bearer ${access}`;
        originalRequest.headers.Authorization = `Bearer ${access}`;
        
        processQueue(null, access);
        return apiClient(originalRequest);
      } catch (err) {
        processQueue(err, null);
        useAuthStore.getState().logout();
        sileo.error('Session expired. Please log in again.');
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    // Parse standard error responses
    if (error.response && error.response.data) {
      const { data } = error.response;
      if (typeof data === 'object' && 'detail' in data) {
        error.message = data.detail;
      } else if (typeof data === 'object' && Object.keys(data).length > 0) {
        const firstErrorKey = Object.keys(data)[0];
        const firstErrorVal = data[firstErrorKey];
        error.message = Array.isArray(firstErrorVal) ? firstErrorVal[0] : firstErrorVal;
      }
    }

    return Promise.reject(error);
  }
);

