import { useAuthStore } from '@/lib/stores/auth-store';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost';

export class KnowledgeSocket {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;
  private knowledgeId: string | null = null;
  private token: string | null = null;
  private closing = false;

  onCanvasUpdate?: (data: { userId: string; elements: unknown[] }) => void;
  onCursorMove?: (data: { userId: string; x: number; y: number }) => void;
  onUserJoin?: (data: { userId: string; userName: string }) => void;
  onUserLeave?: (data: { userId: string }) => void;
  onVersionCreated?: (data: { versionNumber: number }) => void;
  onConnected?: () => void;
  onDisconnected?: (code: number) => void;
  onAuthError?: (code: number) => void;

  connect(knowledgeId: string) {
    this.knowledgeId = knowledgeId;
    this.token = useAuthStore.getState().accessToken;
    if (!this.token) return;
    this.closing = false;
    this.ws = new WebSocket(`${WS_BASE}/ws/knowledge/${knowledgeId}/?token=${this.token}`);
    this.attachListeners();
  }

  private attachListeners() {
    if (!this.ws) return;
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.onConnected?.();
    };
    this.ws.onmessage = e => {
      try {
        const data = JSON.parse(e.data);
        switch (data.type) {
          case 'canvas_update':
            this.onCanvasUpdate?.(data);
            break;
          case 'cursor_move':
            this.onCursorMove?.(data);
            break;
          case 'user_join':
            this.onUserJoin?.(data);
            break;
          case 'user_leave':
            this.onUserLeave?.(data);
            break;
          case 'version_created':
            this.onVersionCreated?.(data);
            break;
        }
      } catch {
        /* ignore malformed frames */
      }
    };
    this.ws.onclose = e => {
      this.stopHeartbeat();
      if (this.closing) return;
      if ([4001, 4002, 4003].includes(e.code)) {
        this.onAuthError?.(e.code);
        return;
      }
      this.onDisconnected?.(e.code);
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnects) return;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      if (this.knowledgeId) this.connect(this.knowledgeId);
    }, delay);
  }

  sendCanvasUpdate(elements: unknown[]) {
    this.send({ action: 'canvas_update', elements });
  }

  sendCursorMove(x: number, y: number) {
    this.send({ action: 'cursor_move', x, y });
  }

  private send(data: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    this.closing = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
    this.knowledgeId = null;
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => this.send({ action: 'heartbeat' }), 40_000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  }
}
