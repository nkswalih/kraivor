export interface Note {
  id: string;
  title: string;
  content: string;
  workspaceId: string;
  projectId?: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  isPinned: boolean;
  tags: string[];
}

export interface NoteCreatePayload {
  title: string;
  content: string;
  projectId?: string;
  tags?: string[];
}

export interface NoteUpdatePayload {
  title?: string;
  content?: string;
  projectId?: string;
  isPinned?: boolean;
  tags?: string[];
}

export interface NoteSearchParams {
  query?: string;
  projectId?: string;
  tags?: string[];
  isPinned?: boolean;
}