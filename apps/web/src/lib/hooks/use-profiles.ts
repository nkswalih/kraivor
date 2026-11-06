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
    mutationFn: (variables: { id: string } & ProfileUpdatePayload) =>
      profileEndpoints.updateProfile(variables.id, variables),
    onSuccess: (updated, variables) => {
      qc.setQueryData(profileKeys.detail(variables.id), updated);
      qc.setQueryData(profileKeys.myProfile(), updated);
      qc.invalidateQueries({ queryKey: profileKeys.all() });
    },
  });
}

export function useUploadProfileImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ field, file }: { field: 'avatar' | 'banner'; file: File }) =>
      profileEndpoints.uploadProfileImage(field, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: profileKeys.myProfile() });
    },
  });
}

export function useFollow(username: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => profileEndpoints.follow(username),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: profileKeys.detail(username) });
      qc.invalidateQueries({ queryKey: profileKeys.followers(username) });
      qc.invalidateQueries({ queryKey: profileKeys.following(username) });
      qc.invalidateQueries({ queryKey: profileKeys.myProfile() });
    },
  });
}

export function useUnfollow(username: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => profileEndpoints.unfollow(username),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: profileKeys.detail(username) });
      qc.invalidateQueries({ queryKey: profileKeys.followers(username) });
      qc.invalidateQueries({ queryKey: profileKeys.following(username) });
      qc.invalidateQueries({ queryKey: profileKeys.myProfile() });
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

export function useUserDiscussions(userId: string) {
  return useQuery({
    queryKey: [...profileKeys.all(), 'discussions', userId],
    queryFn: () => profileEndpoints.listUserDiscussions(userId),
    enabled: !!userId,
    staleTime: 30_000,
  });
}

export function useUserComments(userId: string) {
  return useQuery({
    queryKey: [...profileKeys.all(), 'comments', userId],
    queryFn: () => profileEndpoints.listUserComments(userId),
    enabled: !!userId,
    staleTime: 30_000,
  });
}

export function useProfileSearch(q: string) {
  return useQuery({
    queryKey: [...profileKeys.all(), 'search', q],
    queryFn: () => profileEndpoints.search(q),
    enabled: q.length >= 1,
    staleTime: 30_000,
  });
}

export function useAuthorProfiles(authorIds: string[]) {
  const uniqueIds = authorIds.filter(Boolean);
  return useQuery({
    queryKey: [...profileKeys.all(), 'by-ids', ...uniqueIds.sort()],
    queryFn: () => profileEndpoints.getProfilesByIds(uniqueIds),
    enabled: uniqueIds.length > 0,
    staleTime: 60_000,
    select: data => ({
      profileMap: data.profiles as Record<
        string,
        { username: string; display_name: string; avatar_url: string }
      >,
    }),
  });
}
