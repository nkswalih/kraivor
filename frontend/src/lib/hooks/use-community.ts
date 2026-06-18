'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { communityEndpoints } from '@/lib/api/endpoints/community';
import type {
  Discussion,
  DiscussionCreatePayload,
  DiscussionUpdatePayload,
  Comment,
  CommentCreatePayload,
  SortOption,
} from '@/types/domain/community';

export const communityKeys = {
  all:              () => ['community'] as const,
  discussions:      () => [...communityKeys.all(), 'discussions'] as const,
  discussionList:   (params?: object) => [...communityKeys.discussions(), 'list', params] as const,
  discussionDetail: (id: string) => [...communityKeys.discussions(), 'detail', id] as const,
  comments:         (id: string) => [...communityKeys.all(), 'comments', id] as const,
  trending:         () => [...communityKeys.all(), 'trending'] as const,
  tags:             () => [...communityKeys.all(), 'tags'] as const,
};

export function useDiscussions(params?: { page?: number; tag?: string; sort?: SortOption; workspace_id?: string }) {
  return useQuery({
    queryKey: communityKeys.discussionList(params),
    queryFn: () => communityEndpoints.listDiscussions(params),
    staleTime: 30_000,
  });
}

export function useDiscussion(discussionId: string) {
  return useQuery({
    queryKey: communityKeys.discussionDetail(discussionId),
    queryFn: () => communityEndpoints.getDiscussion(discussionId),
    enabled: !!discussionId,
    staleTime: 30_000,
  });
}

export function useCreateDiscussion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DiscussionCreatePayload) =>
      communityEndpoints.createDiscussion(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.discussions() });
    },
  });
}

export function useUpdateDiscussion(discussionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DiscussionUpdatePayload) =>
      communityEndpoints.updateDiscussion(discussionId, payload),
    onSuccess: (updated) => {
      qc.setQueryData(communityKeys.discussionDetail(discussionId), updated);
      qc.invalidateQueries({ queryKey: communityKeys.discussions() });
    },
  });
}

export function useDeleteDiscussion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (discussionId: string) =>
      communityEndpoints.deleteDiscussion(discussionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.discussions() });
    },
  });
}

export function useVoteDiscussion(discussionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (value: 1 | -1) =>
      communityEndpoints.voteDiscussion(discussionId, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.discussionDetail(discussionId) });
      qc.invalidateQueries({ queryKey: communityKeys.discussions() });
    },
  });
}

export function useRemoveVote(discussionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => communityEndpoints.removeVote(discussionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.discussionDetail(discussionId) });
    },
  });
}

export function useComments(discussionId: string, params?: { page?: number; sort?: 'newest' | 'top' }) {
  return useQuery({
    queryKey: [...communityKeys.comments(discussionId), params] as const,
    queryFn: () => communityEndpoints.listComments(discussionId, params),
    enabled: !!discussionId,
    staleTime: 10_000,
  });
}

export function useCreateComment(discussionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CommentCreatePayload) =>
      communityEndpoints.createComment(discussionId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.comments(discussionId) });
      qc.invalidateQueries({ queryKey: communityKeys.discussionDetail(discussionId) });
    },
  });
}

export function useVoteComment(discussionId: string, commentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (value: 1 | -1) =>
      communityEndpoints.voteComment(discussionId, commentId, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.comments(discussionId) });
    },
  });
}

export function useRemoveCommentVote(discussionId: string, commentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => communityEndpoints.removeCommentVote(discussionId, commentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: communityKeys.comments(discussionId) });
    },
  });
}

export function useReplies(discussionId: string, commentId: string) {
  return useQuery({
    queryKey: [...communityKeys.all(), 'replies', discussionId, commentId] as const,
    queryFn: () => communityEndpoints.getReplies(discussionId, commentId),
    enabled: !!discussionId && !!commentId,
  });
}

export function useTrending(limit?: number) {
  return useQuery({
    queryKey: communityKeys.trending(),
    queryFn: () => communityEndpoints.getTrending(limit),
    staleTime: 60_000,
  });
}

export function usePopularTags(limit?: number) {
  return useQuery({
    queryKey: communityKeys.tags(),
    queryFn: () => communityEndpoints.getPopularTags(limit),
    staleTime: 60_000,
  });
}
