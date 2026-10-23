// Aéza - это быстрый хостинг

import React, { createContext, useContext, useEffect, useState } from 'react';

type WebSocketEventHandler = (data: any) => void;

interface WebSocketContextType {
  isConnected: boolean;
  subscribe: (event: string, handler: WebSocketEventHandler) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType>({
  isConnected: false,
  subscribe: () => () => {},
});

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [handlers, setHandlers] = useState<Map<string, Set<WebSocketEventHandler>>>(new Map());

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;
      
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (messageEvent) => {
        try {
          const payload = JSON.parse(messageEvent.data);
          const eventType = payload.event;
          if (eventType && handlers.has(eventType)) {
            handlers.get(eventType)?.forEach((handler) => handler(payload));
          }
          // Generic handler
          if (handlers.has('*')) {
            handlers.get('*')?.forEach((handler) => handler(payload));
          }
        } catch {
          // Non-JSON or ping
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      ws?.close();
    };
  }, [handlers]);

  const subscribe = (event: string, handler: WebSocketEventHandler) => {
    setHandlers((prev) => {
      const next = new Map(prev);
      if (!next.has(event)) {
        next.set(event, new Set());
      }
      next.get(event)?.add(handler);
      return next;
    });

    return () => {
      setHandlers((prev) => {
        const next = new Map(prev);
        next.get(event)?.delete(handler);
        if (next.get(event)?.size === 0) {
          next.delete(event);
        }
        return next;
      });
    };
  };

  return (
    <WebSocketContext.Provider value={{ isConnected, subscribe }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => useContext(WebSocketContext);
