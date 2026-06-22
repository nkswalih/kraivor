import type { WsServerEvent, WsClientAction } from '@/types/ws';
import { useAuthStore } from '@/lib/stores/auth-store';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost';

export class ChatSocket {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;
  private roomId: string | null = null;
  private token: string | null = null;
  private closing = false;

  onEvent?: (event: WsServerEvent) => void;
  onConnected?: () => void;
  onDisconnected?: (code: number) => void;
  onAuthError?: (code: number) => void;

  connect(roomId: string) {
    this.roomId = roomId;
    this.token = this.getJwt();
    if (!this.token) return;
    this.closing = false;
    this.ws = new WebSocket(`${WS_BASE}/ws/chat/${roomId}/?token=${this.token}`);
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
        this.onEvent?.(data);
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
      this.onDisconnected?.(e.code);
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnects) return;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      if (this.roomId) this.connect(this.roomId);
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
    this.roomId = null;
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => this.send({ action: 'heartbeat' }), 40_000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  }
}
