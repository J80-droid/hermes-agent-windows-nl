import React from 'react';
import { getSessionToken } from './wsAuth';

const h = React.createElement;

/**
 * useFileWatcher — WebSocket client for live file-change events.
 *
 * @returns {{ connected: boolean, lastEvent: object|null, reconnect: number }}
 */
export function useFileWatcher(opts = {}) {
  const { onEvent, reconnectDelay = 3000 } = opts;
  const [connected, setConnected] = React.useState(false);
  const [lastEvent, setLastEvent] = React.useState(null);
  const [reconnect, setReconnect] = React.useState(0);

  React.useEffect(() => {
    const token = getSessionToken();
    if (!token) return undefined;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${
      proto}//${window.location.host}/api/plugins/codebase-viz/events?token=${encodeURIComponent(token)}`;

    let ws;
    let reconnectTimer;
    let destroyed = false;

    function connect() {
      if (destroyed) return;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!destroyed) setConnected(true);
      };

      ws.onclose = () => {
        if (destroyed) return;
        setConnected(false);
        reconnectTimer = setTimeout(() => {
          setReconnect((n) => n + 1);
          connect();
        }, reconnectDelay);
      };

      ws.onmessage = (evt) => {
        if (destroyed) return;
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'changes' && Array.isArray(msg.events)) {
            msg.events.forEach((event) => {
              setLastEvent(event);
              if (typeof onEvent === 'function') onEvent(event);
            });
          } else if (msg.type === 'connected') {
            setConnected(true);
          } else if (msg.type === 'ping') {
            if (ws?.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'pong' }));
            }
          }
        } catch (_e) { /* ignore malformed JSON */ }
      };

      ws.onerror = () => { /* onclose handles reconnect */ };
    }

    connect();

    return () => {
      destroyed = true;
      clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [reconnectDelay]);

  return { connected, lastEvent, reconnect };
}

export function FileWatcherIndicator({ connected }) {
  return h(
    'span',
    {
      className: connected ? 'status-ok' : 'status-err',
      style: { fontSize: '0.75rem', whiteSpace: 'nowrap' },
    },
    connected ? 'Live' : 'Offline',
  );
}

/** Timestamp bump per file-change — dependency voor D3 ripple. */
export function useRippleAnimation(lastEvent) {
  const [ripple, setRipple] = React.useState(null);

  React.useEffect(() => {
    if (!lastEvent) return undefined;
    if (
      lastEvent.is_directory ||
      (lastEvent.type !== 'modified' && lastEvent.type !== 'created')
    ) {
      return undefined;
    }
    setRipple({ path: lastEvent.path, time: Date.now() });
    const timer = setTimeout(() => setRipple(null), 2000);
    return () => clearTimeout(timer);
  }, [lastEvent]);

  return ripple;
}
