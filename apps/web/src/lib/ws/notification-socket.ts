import type { WsServerEvent, WsClientAction } from '@/types/ws';
import { useAuthStore } from '@/lib/stores/auth-store';

function getWsBase(): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL;
  if (configured) return configured;
  if (typeof document === 'undefined') return 'ws://localhost';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl || apiUrl === '/api') {
    const proto = document.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${document.location.host}`;
  }
  const parts = apiUrl.split('://');
  const hostPort = parts.length > 1 ? parts[1] : apiUrl;
  const proto = parts.length > 1 && parts[0] === 'https' ? 'wss:' : 'ws:';
  return `${proto}//${hostPort}`;
}

export class NotificationSocket {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;
  private closing = false;
  private active = false;

  onNotification?: (event: WsServerEvent & { type: 'notification' }) => void;
  onConnected?: () => void;
  onAuthError?: (code: number) => void;

  connect() {
    const token = this.getJwt();
    if (!token) return;
    this.closing = false;
    this.active = true;
    // Use WebSocket subprotocol to pass token (avoids URL exposure in logs/proxies)
    this.ws = new WebSocket(`${getWsBase()}/ws/notifications/`, ['auth', token]);
    this.attachListeners();
  }

  private getJwt(): string | null {
    if (typeof window === 'undefined') return null;
    return useAuthStore.getState().accessToken;
  }

  private attachListeners() {
    if (!this.ws) return;
    const ws = this.ws;
    ws.onopen = () => {
      if (!this.active || this.ws !== ws) return;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.onConnected?.();
    };
    ws.onmessage = e => {
      try {
        const data: WsServerEvent = JSON.parse(e.data);
        if (data.type === 'notification') {
          this.onNotification?.(data);
        }
      } catch {
        // ignore malformed frames
      }
    };
    ws.onclose = e => {
      this.stopHeartbeat();
      if (this.closing || !this.active) return;
      if ([4001, 4002, 4003].includes(e.code)) {
        this.onAuthError?.(e.code);
        return;
      }
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnects || !this.active) return;
    const base = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    const delay = base * (0.5 + Math.random() * 0.5);
    this.reconnectTimer = setTimeout(() => {
      if (!this.active) return;
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
    this.active = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    if (this.ws && this.ws.readyState !== WebSocket.CONNECTING) {
      this.ws.close();
    }
    this.ws = null;
  }

  private startHeartbeat() {
    if (!this.active) return;
    this.heartbeatTimer = setInterval(() => {
      if (!this.active) {
        clearInterval(this.heartbeatTimer!);
        return;
      }
      this.send({ action: 'heartbeat' } as WsClientAction);
    }, 40_000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  }
}
