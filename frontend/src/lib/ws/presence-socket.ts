import { useAuthStore } from '@/lib/stores/auth-store';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost';
const HEARTBEAT_MS = 30_000; // backend presence TTL is 60s

/**
 * App-level presence socket: one per session, opened from the dashboard
 * layout. It is what marks *this* user online for everyone else's members
 * rail, and it hands back the roster of who is already online.
 *
 * Like ChatSocket, the JWT travels as the `auth` subprotocol instead of the
 * URL — the server echoes `auth` back, which is what keeps the browser from
 * failing the handshake per RFC 6455.
 */
export class PresenceSocket {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;
  private closing = false;

  onPresence?: (userId: string, status: 'online' | 'offline') => void;
  onSync?: (userIds: string[]) => void;
  onConnected?: () => void;
  onDisconnected?: (code: number) => void;

  connect() {
    const token =
      typeof window === 'undefined' ? null : useAuthStore.getState().accessToken;
    if (!token) return;
    this.closing = false;
    this.ws = new WebSocket(`${WS_BASE}/ws/presence/`, ['auth', token]);
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
        if (data?.type === 'presence' && data.user_id) {
          this.onPresence?.(data.user_id, data.status);
        } else if (data?.type === 'presence.sync' && Array.isArray(data.user_ids)) {
          this.onSync?.(data.user_ids);
        }
      } catch {
        // ignore malformed frames
      }
    };
    this.ws.onclose = e => {
      this.stopHeartbeat();
      if (this.closing) return;
      this.onDisconnected?.(e.code);
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

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(
      () => this.send({ action: 'heartbeat' }),
      HEARTBEAT_MS
    );
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  }

  private send(action: { action: string }) {
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
}
