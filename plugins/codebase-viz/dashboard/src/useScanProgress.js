import React from 'react';

const API = '/api/plugins/codebase-viz';
const LOG = '[codebase-viz]';

function tabDetail(tab) {
  if (tab === 'sunburst' || tab === 'treemap') return 'LOC tellen (pygount)…';
  if (tab === 'force-graph' || tab === 'dependencies') return 'Python-imports analyseren…';
  if (tab === 'metrics' || tab === 'summary') return 'Metrics samenstellen…';
  return 'Gegevens laden…';
}

function isScanStatusPayload(body) {
  return body && typeof body === 'object' && typeof body.progress === 'number' && 'phase' in body;
}

function mergeScanContext(prev, body, health) {
  const next = { ...prev };
  if (health?.repo_path) next.repoPath = health.repo_path;
  if (health?.pygount_timeout_sec != null) next.timeoutSec = health.pygount_timeout_sec;
  if (health?.scan_mode) next.scanMode = health.scan_mode;
  if (body?.repo_path) next.repoPath = body.repo_path;
  if (body?.repo_label) next.repoLabel = body.repo_label;
  if (body?.timeout_sec != null) next.timeoutSec = body.timeout_sec;
  if (body?.phase) next.phase = body.phase;
  if (body?.scan_mode) next.scanMode = body.scan_mode;
  if (typeof body?.served_from_cache === 'boolean') next.servedFromCache = body.served_from_cache;
  if (typeof body?.stale_age_sec === 'number') next.staleAgeSec = body.stale_age_sec;
  if (typeof body?.refresh_in_background === 'boolean') {
    next.refreshInBackground = body.refresh_in_background;
  } else if (typeof body?.refresh?.running === 'boolean') {
    next.refreshInBackground = body.refresh.running;
  }
  return next;
}

/**
 * Progress while loading. Works with or without GET /scan-status (older dashboards
 * return HTML for unknown routes — we fall back to a local elapsed timer).
 */
export function useScanProgress(active, tab) {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const startRef = React.useRef(0);
  const [elapsedSec, setElapsedSec] = React.useState(0);
  const [serverStatus, setServerStatus] = React.useState(null);
  const [useLocalOnly, setUseLocalOnly] = React.useState(false);
  const [legacyBackend, setLegacyBackend] = React.useState(false);
  const [apiPath, setApiPath] = React.useState('');
  const [serverVersion, setServerVersion] = React.useState('');
  const [scanContext, setScanContext] = React.useState({
    repoPath: '',
    repoLabel: '',
    timeoutSec: null,
    phase: '',
    scanMode: '',
    servedFromCache: null,
    staleAgeSec: null,
    refreshInBackground: false,
  });
  const warnedRef = React.useRef(false);
  const sdkRef = React.useRef(SDK);
  sdkRef.current = SDK;

  React.useEffect(() => {
    if (!active) {
      startRef.current = 0;
      setElapsedSec(0);
      setServerStatus(null);
      setUseLocalOnly(false);
      setLegacyBackend(false);
      setApiPath('');
      setServerVersion('');
      setScanContext({
        repoPath: '',
        repoLabel: '',
        timeoutSec: null,
        phase: '',
        scanMode: '',
        servedFromCache: null,
        staleAgeSec: null,
        refreshInBackground: false,
      });
      warnedRef.current = false;
      return undefined;
    }

    startRef.current = Date.now();
    const tick = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);

    return () => window.clearInterval(tick);
  }, [active, tab]);

  React.useEffect(() => {
    const fetchJSON = sdkRef.current?.fetchJSON;
    if (!active || !fetchJSON) return undefined;

    let cancelled = false;
    let pollId = null;

    const stopPolling = () => {
      if (pollId != null) {
        window.clearInterval(pollId);
        pollId = null;
      }
    };

    const enableLocal = (reason) => {
      stopPolling();
      if (!warnedRef.current) {
        warnedRef.current = true;
        console.info(
          LOG,
          'voortgang via lokale timer',
          reason || '(herstart dashboard met nieuwste plugin_api voor server-status)',
        );
      }
      setUseLocalOnly(true);
    };

    const pollScanStatus = () => {
      fetchJSON(`${API}/scan-status`)
        .then((body) => {
          if (cancelled) return;
          if (isScanStatusPayload(body)) {
            setServerStatus(body);
            setScanContext((prev) => mergeScanContext(prev, body, null));
          } else {
            enableLocal('scan-status antwoord ongeldig');
          }
        })
        .catch((err) => {
          if (!cancelled) enableLocal(err?.message || String(err));
        });
    };

    fetchJSON(`${API}/health`)
      .then((health) => {
        if (cancelled) return;
        if (typeof health?.version === 'string') {
          setServerVersion(health.version);
        }
        if (typeof health?.plugin_api_path === 'string') {
          setApiPath(health.plugin_api_path);
        }
        setScanContext((prev) => mergeScanContext(prev, null, health));
        if (typeof health?.pygount_timeout_sec === 'number') {
          setLegacyBackend(false);
          pollScanStatus();
          pollId = window.setInterval(pollScanStatus, 800);
        } else {
          setLegacyBackend(true);
          enableLocal('oude plugin_api (geen pygount_timeout_sec in /health)');
        }
      })
      .catch(() => {
        if (!cancelled) enableLocal('health niet bereikbaar');
      });

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [active, tab]);

  const detail = useLocalOnly
    ? tabDetail(tab)
    : serverStatus?.detail || tabDetail(tab);

  const progress = useLocalOnly
    ? Math.min(90, 10 + elapsedSec * 4)
    : typeof serverStatus?.progress === 'number'
      ? serverStatus.progress
      : Math.min(90, 10 + elapsedSec * 4);

  const elapsed =
    !useLocalOnly && serverStatus?.elapsed_sec != null
      ? `${serverStatus.elapsed_sec}s`
      : elapsedSec > 0
        ? `${elapsedSec}s`
        : '';

  const maxSec = scanContext.timeoutSec;
  const elapsedWithMax =
    elapsed && maxSec != null ? `${elapsed} / max ${maxSec}s` : elapsed;

  return {
    detail,
    progress,
    elapsed: elapsedWithMax,
    busy: useLocalOnly
      ? elapsedSec < 600
      : serverStatus == null
        ? true
        : serverStatus.busy !== false,
    legacyApi: legacyBackend,
    apiPath,
    serverVersion,
    repoPath: scanContext.repoPath,
    repoLabel: scanContext.repoLabel || scanContext.repoPath,
    timeoutSec: scanContext.timeoutSec,
    phase: scanContext.phase || serverStatus?.phase || '',
    scanMode: scanContext.scanMode,
    servedFromCache: scanContext.servedFromCache,
    staleAgeSec: scanContext.staleAgeSec,
    refreshInBackground: scanContext.refreshInBackground,
  };
}
