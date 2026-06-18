export type WsClientAction =
  | { action: 'message'; content: string; content_type?: string; mentions?: string[]; reply_to?: string }
  | { action: 'typing.start' }
  | { action: 'typing.stop' }
  | { action: 'mark_read'; message_id: string }
  | { action: 'delete'; message_id: string }
  | { action: 'heartbeat' }
  | { action: 'mark_all_read' }
  | { action: 'dismiss'; notification_id?: string };

export type WsServerEvent =
  | { type: 'message'; message_id: string; sender_id: string; sender_name: string; content: string; content_type: string; reply_to: string; mentions: string[]; created_at: string }
  | { type: 'typing.start' | 'typing.stop'; user_id: string; user_name: string }
  | { type: 'presence'; user_id: string; status: 'online' | 'offline' }
  | { type: 'notification'; id: string; notification_type: string; title: string; body: string; link: string; workspace_id: string; actor_id: string; created_at: string };
