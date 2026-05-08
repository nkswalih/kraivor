export interface Workspace {
  id: string;
  name: string;
  slug: string;
  logo?: string;
  description?: string;
  plan: WorkspacePlan;
  createdAt: string;
  updatedAt: string;
  members: WorkspaceMember[];
  settings: WorkspaceSettings;
}

export enum WorkspacePlan {
  FREE = 'free',
  STARTER = 'starter',
  PROFESSIONAL = 'professional',
  ENTERPRISE = 'enterprise',
}

export interface WorkspaceMember {
  userId: string;
  role: WorkspaceRole;
  joinedAt: string;
  user: {
    id: string;
    name: string;
    email: string;
    avatar?: string;
  };
}

export enum WorkspaceRole {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer',
}

export interface WorkspaceSettings {
  defaultRole: WorkspaceRole;
  allowGuestAccess: boolean;
  twoFactorRequired: boolean;
  sessionTimeout: number;
}

export interface CreateWorkspacePayload {
  name: string;
  slug: string;
  description?: string;
}

export interface UpdateWorkspacePayload {
  name?: string;
  description?: string;
  logo?: string;
}