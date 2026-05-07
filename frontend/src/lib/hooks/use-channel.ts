'use client';

import { useEffect, useRef, useCallback, useState } from 'react';

interface UseRealtimeOptions<T> {
  url: string;
  onMessage?: (data: T) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useRealtime<T>({ url, onMessage, onConnect, onDisconnect, reconnectAttempts = 5, reconnectInterval = 3000 }: UseRealtimeOptions<T>) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectCountRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
      reconnectCountRef.current = 0;
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as T;
        onMessage?.(data);
      } catch {
        onMessage?.(event.data as unknown as T);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      onDisconnect?.();

      if (reconnectCountRef.current < reconnectAttempts) {
        reconnectCountRef.current++;
        setTimeout(connect, reconnectInterval);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [url, onMessage, onConnect, onDisconnect, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { isConnected, send, disconnect, reconnect: connect };
}