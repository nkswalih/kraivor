import { identityApi } from '@/lib/api/client';
import type { Profile, ProfileUpdatePayload } from '@/types/domain/profiles';

export interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  notifications_enabled: boolean;
  email_notifications: boolean;
  push_notifications: boolean;
  desktop_notifications: boolean;
  notification_frequency: 'realtime' | 'hourly' | 'daily' | 'never';
  language: string;
  timezone: string;
  default_home_view: string;
  emoji_translation: boolean;
}

export interface Session {
  session_id: string;
  device_name: string;
  device_type: string;
  ip_address: string;
  last_used_at: string;
  created_at: string;
  is_current: boolean;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at?: string;
}

export interface CreateApiKeyResponse {
  id: string;
  name: string;
  key: string;
  created_at: string;
}

export interface OAuthApp {
  provider: string;
  name: string;
  connected_at: string;
  scopes: string[];
  avatar_url?: string;
}

export interface BillingPlan {
  id: string;
  name: string;
  price: number;
  currency: string;
  interval: 'month' | 'year';
  features: string[];
  is_current: boolean;
}

export interface Invoice {
  id: string;
  amount: number;
  currency: string;
  status: 'paid' | 'pending' | 'failed';
  issued_at: string;
  paid_at?: string;
  pdf_url?: string;
}

export const settingsEndpoints = {
  getSettings: () => identityApi.get<UserSettings>('/auth/settings/'),

  updateSettings: (payload: Partial<UserSettings>) =>
    identityApi.patch<UserSettings>('/auth/settings/', payload),

  getSessions: () => identityApi.get<{ sessions: Session[] }>('/auth/sessions/'),

  revokeSession: (sessionId: string) =>
    identityApi.delete<void>(`/auth/sessions/${sessionId}/`),

  revokeAllSessions: () => identityApi.delete<void>('/auth/sessions/all/'),

  getApiKeys: async () => {
    const data = await identityApi.get<{ keys: ApiKey[]; results: ApiKey[] } | ApiKey[]>('/auth/api-keys/');
    if (Array.isArray(data)) return data;
    if (data?.keys) return data.keys;
    if (data?.results) return data.results;
    return [];
  },

  createApiKey: (name: string) =>
    identityApi.post<CreateApiKeyResponse>('/auth/api-keys/', { name }),

  revokeApiKey: (keyId: string) =>
    identityApi.delete<void>(`/auth/api-keys/${keyId}/`),

  getOAuthApps: () => identityApi.get<OAuthApp[]>('/auth/oauth/apps/'),

  disconnectOAuthApp: (provider: string) =>
    identityApi.delete<void>(`/auth/oauth/${provider}/disconnect/`),

  getMyProfile: () => identityApi.get<Profile>('/profiles/me/'),

  updateProfile: (username: string, payload: ProfileUpdatePayload) =>
    identityApi.patch<Profile>(`/profiles/${username}/`, payload),

  uploadProfileImage: (field: 'avatar' | 'banner', file: File) => {
    const formData = new FormData();
    formData.append('field', field);
    formData.append('file', file);
    return identityApi.post<{ url: string; key: string }>('/profiles/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getBillingPlan: () => identityApi.get<BillingPlan>('/billing/plan/'),

  getInvoices: () => identityApi.get<{ invoices: Invoice[] }>('/billing/invoices/'),
};
