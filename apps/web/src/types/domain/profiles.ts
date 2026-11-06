export interface Profile {
  id: string;
  user_id: string;
  username: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  user_avatar_url?: string;
  banner_url: string;
  website_url: string;
  github_username: string;
  twitter_username: string;
  linkedin_url: string;
  location: string;
  is_public: boolean;
  is_following: boolean;
  is_owner: boolean;
  reputation_score: number;
  followers_count: number;
  following_count: number;
  discussion_count: number;
  comment_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdatePayload {
  username?: string;
  display_name?: string;
  bio?: string;
  avatar_url?: string;
  banner_url?: string;
  website_url?: string;
  github_username?: string;
  twitter_username?: string;
  linkedin_url?: string;
  location?: string;
  is_public?: boolean;
}

export interface ProfileSearchParams {
  q: string;
  page?: number;
}

export interface Follower {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  user_avatar_url?: string;
  bio: string;
  followed_at: string;
}

export interface TopContributor {
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  user_avatar_url?: string;
  reputation_score: number;
  discussion_count: number;
  comment_count: number;
}
