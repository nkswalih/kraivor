'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { profileEndpoints } from '@/lib/api/endpoints/profiles';
import type { Profile, ProfileUpdatePayload } from '@/types/domain/profiles';

export const profileKeys = {
  all: () => ['profiles'] as const,
  detail: (username: string) => [...profileKeys.all(), 'detail', username] as const,
  myProfile: () => [...profileKeys.all(), 'me'] as const,
  followers: (username: string) => [...profileKeys.all(), 'followers', username] as const,
  following: (username: string) => [...profileKeys.all(), 'following', username] as const,
  leaderboard: () => [...profileKeys.all(), 'leaderboard'] as const,
  contributors: () => [...profileKeys.all(), 'contributors'] as const,
};

export function useMyProfile() {
  return useQuery({
    queryKey: profileKeys.myProfile(),
    queryFn: () => profileEndpoints.getMyProfile(),
    staleTime: 30_000,
  });
}

export function useProfile(username: string) {
  return useQuery({
    queryKey: profileKeys.detail(username),
    queryFn: () => profileEndpoints.getProfile(username),
    enabled: !!username,
    staleTime: 30_000,
  });
}

export function useCheckUsername(username: string) {
  return useQuery({
    queryKey: [...profileKeys.all(), 'check-username', username],
    queryFn: () => profileEndpoints.checkUsername(username),
    enabled: username.length >= 3,
    staleTime: 5_000,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ username, ...payload }: { username: string } & ProfileUpdatePayload) =>
      profileEndpoints.updateProfile(username, payload),
    onSuccess: (updated, variables) => {
      qc.setQueryData(profileKeys.detail(variables.username), updated);
      qc.setQueryData(profileKeys.myProfile(), updated);
    },
  });
}

export function useUploadProfileImage() {
  return useMutation({
    mutationFn: ({ field, file }: { field: 'avatar' | 'banner'; file: File }) =>
      profileEndpoints.uploadProfileImage(field, file),
  });
}

export function useFollow(username: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => profileEndpoints.follow(username),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: profileKeys.detail(username) });
    },
  });
}

export function useUnfollow(username: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => profileEndpoints.unfollow(username),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: profileKeys.detail(username) });
    },
  });
}

export function useFollowers(username: string) {
  return useQuery({
    queryKey: profileKeys.followers(username),
    queryFn: () => profileEndpoints.getFollowers(username),
    enabled: !!username,
    staleTime: 30_000,
  });
}

export function useFollowing(username: string) {
  return useQuery({
    queryKey: profileKeys.following(username),
    queryFn: () => profileEndpoints.getFollowing(username),
    enabled: !!username,
    staleTime: 30_000,
  });
}

export function useLeaderboard() {
  return useQuery({
    queryKey: profileKeys.leaderboard(),
    queryFn: () => profileEndpoints.getLeaderboard(),
    staleTime: 60_000,
  });
}

export function useTopContributors(limit?: number) {
  return useQuery({
    queryKey: profileKeys.contributors(),
    queryFn: () => profileEndpoints.getTopContributors(limit),
    staleTime: 60_000,
  });
}
