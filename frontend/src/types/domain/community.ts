export interface Tag {
  id: string;
  name: string;
  slug: string;
  description: string;
  usage_count: number;
  created_at: string;
}

export interface Discussion {
  id: string;
  workspace_id: string | null;
  title: string;
  body: string;
  author_id: string;
  author_username: string;
  author_display_name: string;
  author_avatar_url: string;
  upvote_count: number;
  downvote_count: number;
  comment_count: number;
  tags: Tag[];
  is_pinned: boolean;
  is_locked: boolean;
  is_resolved: boolean;
  user_vote: number | null;
  created_at: string;
  updated_at: string;
}

export interface DiscussionCreatePayload {
  title: string;
  body: string;
  workspace_id?: string | null;
  tags?: string[];
  author_username: string;
  author_display_name: string;
  author_avatar_url?: string;
}

export interface DiscussionUpdatePayload {
  title?: string;
  body?: string;
  tags?: string[];
  is_resolved?: boolean;
}

export interface Comment {
  id: string;
  discussion_id: string;
  parent_id: string | null;
  body: string;
  author_id: string;
  author_username: string;
  author_display_name: string;
  author_avatar_url: string;
  upvote_count: number;
  downvote_count: number;
  user_vote: number | null;
  reply_count: number;
  created_at: string;
  updated_at: string;
}

export interface CommentCreatePayload {
  body: string;
  parent_id?: string | null;
  author_username: string;
  author_display_name: string;
  author_avatar_url?: string;
}

export interface PaginatedResponse<T> {
  results: T[];
  total: number;
  page: number;
  page_size: number;
}

export type SortOption = 'latest' | 'trending' | 'top';
export type ActiveTab = 'home' | 'trending' | 'explore' | 'news';
export type ViewMode = 'list' | 'grid';
