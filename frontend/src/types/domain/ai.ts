export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  attachments?: MessageAttachment[];
  status: MessageStatus;
}

export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

export enum MessageStatus {
  SENDING = 'sending',
  SENT = 'sent',
  ERROR = 'error',
}

export interface MessageAttachment {
  type: AttachmentType;
  url: string;
  name: string;
  size?: number;
}

export enum AttachmentType {
  FILE = 'file',
  CODE = 'code',
  IMAGE = 'image',
  REPOSITORY = 'repository',
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  context?: ChatContext;
}

export interface ChatContext {
  repositoryId?: string;
  projectId?: string;
  analysisId?: string;
}

export interface SendMessagePayload {
  content: string;
  sessionId?: string;
  context?: ChatContext;
  attachments?: File[];
}