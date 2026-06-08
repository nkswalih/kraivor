export interface ApiError {
  message: string;
  code: string;
  statusCode: number;
  details?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
}

export interface ApiRequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean | undefined>;
  data?: unknown;
  timeout?: number;
}

export interface QueueItem {
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
  config: unknown;
}

export type ApiErrorCode =
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'RATE_LIMITED'
  | 'SERVER_ERROR'
  | 'NETWORK_ERROR'
  | 'TIMEOUT';

export interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  retryCondition?: (error: ApiError) => boolean;
}

/* ─── Core Backend API Types (from core service) ────────────────── */

export interface JwtUser {
  user_id: string;
  user_name: string;
  email: string;
  workspace_ids: string[];
  roles: Record<string, 'owner' | 'admin' | 'member' | 'viewer'>;
}

export interface ChatRoom {
  id: string;
  workspace: string;
  name: string;
  room_type: 'workspace' | 'group' | 'ai' | 'dm';
  room_type_display: string;
  topic: string;
  is_active: boolean;
  last_message_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  message_id: string;
  room_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  content_type: string;
  reply_to: string;
  mentions: string[];
  attachment_url: string;
  created_at: string;
  edited_at: string;
  deleted_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  plan: 'free' | 'pro' | 'team' | 'enterprise';
  avatar_url: string | null;
  description: string | null;
  active_member_count: number;
  current_user_role: string | null;
  owner_id?: string;
  settings?: Record<string, unknown>;
  members?: WorkspaceMember[];
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMember {
  id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  status: 'active' | 'removed';
  joined_at: string | null;
  invited_by_id: string | null;
  created_at: string;
  updated_at: string;
  user?: {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
  };
}

export interface WorkspaceInvitation {
  id: string;
  workspace_id: string;
  workspace_name: string;
  email: string;
  role: string;
  token: string;
  status: 'pending' | 'accepted' | 'expired' | 'revoked';
  accept_url: string;
  expires_at: string;
  created_at: string;
}

export interface Repository {
  id: string;
  workspace_id: string;
  github_repo: string;
  github_id: number;
  default_branch: string;
  language: string | null;
  description: string | null;
  is_private: boolean;
  last_analyzed_at: string | null;
  last_analysis_score: number | null;
  indexed: boolean;
  connected_by_id: string | null;
  status: 'connected' | 'disconnected';
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSpace {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  created_by: string;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  canvas_data?: Record<string, unknown>;
}

export interface Notification {
  id: string;
  user_id: string;
  workspace: string | null;
  notification_type: string;
  title: string;
  body: string;
  link: string;
  actor_id: string | null;
  read_at: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface CursorPage<T> {
  results: T[];
  has_next: boolean;
  next_start_key?: string;
}

export interface CursorPageLegacy<T> {
  results: T[];
  next?: string | null;
  previous?: string | null;
}

export interface InvitationAcceptResponse {
  workspace_id: string;
  workspace_name: string;
  workspace_slug: string;
  role: string;
  joined_at: string;
  message: string;
}

export interface CreateRoomPayload {
  name: string;
  room_type?: 'workspace' | 'group' | 'ai' | 'dm';
  topic?: string;
}

export interface SendMessagePayload {
  content: string;
  content_type?: string;
  mentions?: string[];
  reply_to?: string;
}

export interface CreateKnowledgePayload {
  name: string;
  description?: string;
  canvas_data?: Record<string, unknown>;
}

export interface UpdateKnowledgePayload {
  name?: string;
  description?: string;
  canvas_data?: Record<string, unknown>;
}

export interface InviteMemberPayload {
  email: string;
  role?: 'admin' | 'member' | 'viewer';
}

export interface ConnectRepoPayload {
  github_repo: string;
}

export interface MarkAllReadResponse {
  status: string;
  marked_read: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}
