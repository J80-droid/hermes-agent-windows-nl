import React from 'react';

const API = '/api/plugins/codebase-viz';
const LOG = '[codebase-viz]';

export function usePluginFetch(path, deps = [], refreshToken = 0) {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!SDK?.fetchJSON || !path) return undefined;
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    const url = `${API}${path}`;
    console.info(LOG, 'fetch start', url);
    SDK.fetchJSON(url, { signal: ac.signal })
      .then((body) => {
        if (!ac.signal.aborted) {
          console.info(LOG, 'fetch ok', url, {
            fallback: body?.fallback,
            error: body?.error,
            keys: body && typeof body === 'object' ? Object.keys(body) : [],
          });
          setData(body);
        }
      })
      .catch((err) => {
        if (err?.name !== 'AbortError' && !ac.signal.aborted) {
          console.error(LOG, 'fetch fail', url, err);
          setError(err);
        }
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [path, refreshToken, ...deps]);

  return { data, error, loading };
}

export async function postForceScan() {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK?.fetchJSON) return;
  await SDK.fetchJSON(`${API}/force-scan`, { method: 'POST' });
}

export function useD3Loader() {
  const [ready, setReady] = React.useState(!!window.d3);

  React.useEffect(() => {
    if (window.d3) {
      setReady(true);
      return undefined;
    }
    const src = '/dashboard-plugins/codebase-viz/dist/d3.v7.min.js';
    const existing = document.querySelector(`script[data-codebase-viz-d3="1"]`);
    if (existing) {
      existing.addEventListener('load', () => setReady(true));
      return undefined;
    }
    const s = document.createElement('script');
    s.src = src;
    s.async = true;
    s.dataset.codebaseVizD3 = '1';
    s.onload = () => setReady(true);
    s.onerror = () => setReady(false);
    document.head.appendChild(s);
    return () => {};
  }, []);

  return ready;
}
