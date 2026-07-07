import { identityApi, identityRequest, coreApi } from '@/lib/api/client';
import type {
  Profile,
  ProfileUpdatePayload,
  Follower,
  TopContributor,
} from '@/types/domain/profiles';
import type { Discussion, Comment, PaginatedResponse } from '@/types/domain/community';

export const profileEndpoints = {
  getProfilesByIds: (userIds: string[]) =>
    identityApi.post<{
      profiles: Record<
        string,
        { display_name: string; avatar_url: string; user_avatar_url: string; username: string }
      >;
    }>('/profiles/by-ids/', { user_ids: userIds }),

  getMyProfile: () => identityApi.get<Profile>('/profiles/me/'),

  getProfile: (username: string) => identityApi.get<Profile>(`/profiles/${username}/`),

  updateProfile: (username: string, payload: ProfileUpdatePayload) =>
    identityApi.patch<Profile>(`/profiles/${username}/`, payload),

  uploadProfileImage: (field: 'avatar' | 'banner', file: File) => {
    const formData = new FormData();
    formData.append('field', field);
    formData.append('file', file);
    return identityRequest<{ url: string; key: string }>('/profiles/upload/', {
      method: 'POST',
      body: formData,
    });
  },

  checkUsername: (username: string) =>
    identityApi.get<{ username: string; available: boolean }>(
      `/profiles/check-username/?username=${encodeURIComponent(username)}`
    ),

  search: (q: string, page?: number) => {
    const qs = new URLSearchParams({ q });
    if (page) qs.set('page', String(page));
    return identityApi.get<{ results: Profile[]; total: number; page: number; page_size: number }>(
      `/profiles/search/?${qs.toString()}`
    );
  },

  getFollowers: (username: string, page?: number) => {
    const qs = page ? `?page=${page}` : '';
    return identityApi.get<{ results: Follower[]; total: number; page: number; page_size: number }>(
      `/profiles/${username}/followers/${qs}`
    );
  },

  getFollowing: (username: string, page?: number) =>
    identityApi.get<{ results: Follower[]; total: number; page: number; page_size: number }>(
      `/profiles/${username}/following/${page ? `?page=${page}` : ''}`
    ),

  follow: (username: string) => identityApi.post<void>(`/profiles/${username}/follow/`),

  unfollow: (username: string) => identityApi.delete<void>(`/profiles/${username}/follow/`),

  getFollowStatus: (username: string) =>
    identityApi.get<{ is_following: boolean }>(`/profiles/${username}/follow/status/`),

  getLeaderboard: (page?: number) => {
    const qs = page ? `?page=${page}` : '';
    return identityApi.get<{ results: Profile[]; total: number; page: number; page_size: number }>(
      `/profiles/leaderboard/${qs}`
    );
  },

  getTopContributors: (limit?: number) => {
    const qs = limit ? `?limit=${limit}` : '';
    return identityApi.get<{ results: TopContributor[] }>(`/profiles/top-contributors/${qs}`);
  },

  listUserDiscussions: (userId: string, params?: { page?: number }) => {
    const qs = params?.page ? `?page=${params.page}` : '';
    return coreApi.get<PaginatedResponse<Discussion>>(`/community/user/${userId}/discussions/${qs}`);
  },

  listUserComments: (userId: string, params?: { page?: number }) => {
    const qs = params?.page ? `?page=${params.page}` : '';
    return coreApi.get<PaginatedResponse<Comment>>(`/community/user/${userId}/comments/${qs}`);
  },
};
