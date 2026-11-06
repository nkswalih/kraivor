'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsEndpoints } from '@/lib/api/endpoints/settings';
import type { UserSettings } from '@/lib/api/endpoints/settings';

export const settingsKeys = {
  all: () => ['settings'] as const,
  user: () => [...settingsKeys.all(), 'user'] as const,
  sessions: () => [...settingsKeys.all(), 'sessions'] as const,
  apiKeys: () => [...settingsKeys.all(), 'api-keys'] as const,
  oauth: () => [...settingsKeys.all(), 'oauth'] as const,
  billing: () => [...settingsKeys.all(), 'billing'] as const,
  invoices: () => [...settingsKeys.all(), 'invoices'] as const,
};

export function useUserSettings() {
  return useQuery({
    queryKey: settingsKeys.user(),
    queryFn: () => settingsEndpoints.getSettings(),
    staleTime: 60_000,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<UserSettings>) => settingsEndpoints.updateSettings(payload),
    onSuccess: data => {
      qc.setQueryData(settingsKeys.user(), data);
    },
  });
}

export function useSessions() {
  return useQuery({
    queryKey: settingsKeys.sessions(),
    queryFn: () => settingsEndpoints.getSessions(),
    staleTime: 30_000,
  });
}

export function useRevokeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => settingsEndpoints.revokeSession(sessionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.sessions() }),
  });
}

export function useRevokeAllSessions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => settingsEndpoints.revokeAllSessions(),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.sessions() }),
  });
}

export function useApiKeys() {
  return useQuery({
    queryKey: settingsKeys.apiKeys(),
    queryFn: () => settingsEndpoints.getApiKeys(),
    staleTime: 30_000,
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => settingsEndpoints.createApiKey(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.apiKeys() }),
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => settingsEndpoints.revokeApiKey(keyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.apiKeys() }),
  });
}

export function useOAuthApps() {
  return useQuery({
    queryKey: settingsKeys.oauth(),
    queryFn: () => settingsEndpoints.getOAuthApps(),
    staleTime: 60_000,
  });
}

export function useDisconnectOAuthApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => settingsEndpoints.disconnectOAuthApp(provider),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.oauth() }),
  });
}

export function useMyProfile() {
  return useQuery({
    queryKey: [...settingsKeys.all(), 'my-profile'] as const,
    queryFn: () => settingsEndpoints.getMyProfile(),
    staleTime: 30_000,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ username, ...payload }: { username: string } & Record<string, unknown>) =>
      settingsEndpoints.updateProfile(username, payload),
    onSuccess: (data) => {
      qc.setQueryData([...settingsKeys.all(), 'my-profile'] as const, data);
      qc.invalidateQueries({ queryKey: ['profiles'] });
    },
  });
}

export function useUploadProfileImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ field, file }: { field: 'avatar' | 'banner'; file: File }) =>
      settingsEndpoints.uploadProfileImage(field, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...settingsKeys.all(), 'my-profile'] as const });
      qc.invalidateQueries({ queryKey: ['profiles'] });
    },
  });
}

export function useBillingPlan() {
  return useQuery({
    queryKey: settingsKeys.billing(),
    queryFn: () => settingsEndpoints.getBillingPlan(),
    staleTime: 120_000,
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: settingsKeys.invoices(),
    queryFn: () => settingsEndpoints.getInvoices(),
    staleTime: 120_000,
  });
}
