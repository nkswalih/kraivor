import { coreApi } from '@/lib/api/client';
import type {
  Discussion,
  DiscussionCreatePayload,
  DiscussionUpdatePayload,
  Comment,
  CommentCreatePayload,
  PaginatedResponse,
  Tag,
  SortOption,
} from '@/types/domain/community';

export const communityEndpoints = {
  listDiscussions: (params?: {
    page?: number;
    tag?: string;
    sort?: SortOption;
    workspace_id?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.tag) qs.set('tag', params.tag);
    if (params?.sort) qs.set('sort', params.sort);
    if (params?.workspace_id) qs.set('workspace_id', params.workspace_id);
    const query = qs.toString();
    return coreApi.get<PaginatedResponse<Discussion>>(`/community/${query ? `?${query}` : ''}`);
  },

  getDiscussion: (discussionId: string) => coreApi.get<Discussion>(`/community/${discussionId}/`),

  createDiscussion: (payload: DiscussionCreatePayload) =>
    coreApi.post<Discussion>('/community/', payload),

  updateDiscussion: (discussionId: string, payload: DiscussionUpdatePayload) =>
    coreApi.patch<Discussion>(`/community/${discussionId}/`, payload),

  deleteDiscussion: (discussionId: string) => coreApi.delete<void>(`/community/${discussionId}/`),

  voteDiscussion: (discussionId: string, value: 1 | -1) =>
    coreApi.post<{ value: number; action: string }>(`/community/${discussionId}/vote/`, { value }),

  removeVote: (discussionId: string) => coreApi.delete<void>(`/community/${discussionId}/vote/`),

  listComments: (discussionId: string, params?: { page?: number; sort?: 'newest' | 'top' }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.sort) qs.set('sort', params.sort);
    const query = qs.toString();
    return coreApi.get<PaginatedResponse<Comment>>(
      `/community/${discussionId}/comments/${query ? `?${query}` : ''}`
    );
  },

  createComment: (discussionId: string, payload: CommentCreatePayload) =>
    coreApi.post<Comment>(`/community/${discussionId}/comments/`, payload),

  getReplies: (discussionId: string, commentId: string) =>
    coreApi.get<Comment[]>(`/community/${discussionId}/comments/${commentId}/`),

  voteComment: (discussionId: string, commentId: string, value: 1 | -1) =>
    coreApi.post<{ value: number; action: string }>(
      `/community/${discussionId}/comments/${commentId}/vote/`,
      { value }
    ),

  removeCommentVote: (discussionId: string, commentId: string) =>
    coreApi.delete<void>(`/community/${discussionId}/comments/${commentId}/vote/`),

  getTrending: (limit?: number) => {
    const qs = limit ? `?limit=${limit}` : '';
    return coreApi.get<{ results: Discussion[] }>(`/community/trending/${qs}`);
  },

  getPopularTags: (limit?: number) => {
    const qs = limit ? `?limit=${limit}` : '';
    return coreApi.get<{ results: Tag[] }>(`/community/tags/popular/${qs}`);
  },

  searchTags: (q: string) =>
    coreApi.get<{ results: Tag[] }>(`/community/tags/search/?q=${encodeURIComponent(q)}`),
};
