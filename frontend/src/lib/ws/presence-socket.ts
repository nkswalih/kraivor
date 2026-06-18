const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost';

export class PresenceSocket {
  private ws: WebSocket | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 10;

  onConnected?: () => void;
  onAuthError?: (code: number) => void;

  connect() {
    const token = this.getJwt();
    if (!token) return;
    this.ws = new WebSocket(`${WS_BASE}/ws/presence/?token=${token}`);
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
      this.startHeartbeat();
      this.onConnected?.();
    };
    this.ws.onclose = (e) => {
      this.stopHeartbeat();
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

  sendHeartbeat() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'heartbeat' }));
    }
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => this.sendHeartbeat(), 30_000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }
}
