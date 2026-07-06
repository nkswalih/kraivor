import type { WsServerEvent, WsClientAction } from '@/types/ws';
import { useAuthStore } from '@/lib/stores/auth-store';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost';

export class NotificationSocket {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;
  private closing = false;

  onNotification?: (event: WsServerEvent & { type: 'notification' }) => void;
  onConnected?: () => void;
  onAuthError?: (code: number) => void;

  connect() {
    const token = this.getJwt();
    if (!token) return;
    this.closing = false;
    this.ws = new WebSocket(`${WS_BASE}/ws/notifications/?token=${token}`);
    this.attachListeners();
  }

  private getJwt(): string | null {
    if (typeof window === 'undefined') return null;
    return useAuthStore.getState().accessToken;
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
        const data: WsServerEvent = JSON.parse(e.data);
        if (data.type === 'notification') {
          this.onNotification?.(data);
        }
      } catch {
        // ignore malformed frames
      }
    };
    this.ws.onclose = e => {
      this.stopHeartbeat();
      if (this.closing) return;
      if ([4001, 4002, 4003].includes(e.code)) {
        this.onAuthError?.(e.code);
        return;
      }
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnects) return;
    const base = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    const delay = base * (0.5 + Math.random() * 0.5);
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
    this.closing = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => this.send({ action: 'heartbeat' } as WsClientAction), 40_000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  }
}
