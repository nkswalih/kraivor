import type { WsServerEvent, WsClientAction } from '@/types/ws';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost';

export class NotificationSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;

  onNotification?: (event: WsServerEvent & { type: 'notification' }) => void;
  onConnected?: () => void;
  onAuthError?: (code: number) => void;

  connect() {
    const token = this.getJwt();
    if (!token) return;
    this.ws = new WebSocket(`${WS_BASE}/ws/notifications/?token=${token}`);
    this.attachListeners();
  }

  private getJwt(): string | null {
    if (typeof window === 'undefined') return null;
    try {
      const raw = localStorage.getItem('kraivor-auth');
      if (raw) {
        const parsed = JSON.parse(raw);
        return parsed?.state?.accessToken ?? null;
      }
      return null;
    } catch {
      return null;
    }
  }

  private attachListeners() {
    if (!this.ws) return;
    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onConnected?.();
    };
    this.ws.onmessage = e => {
      try {
        const data: WsServerEvent = JSON.parse(e.data);
        if (data.type === 'notification') {
          this.onNotification?.(data);
        }
      } catch {
        // ignore malformed frames
      }
    };
    this.ws.onclose = e => {
      if ([4001, 4002, 4003].includes(e.code)) {
        this.onAuthError?.(e.code);
        return;
      }
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnects) return;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  send(action: WsClientAction) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(action));
    }
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}
