import React from 'react';
import { useScanProgress } from './useScanProgress';

const h = React.createElement;
const LOG = '[codebase-viz]';

export default function ScanProgress({ active, tab }) {
  const {
    detail,
    progress,
    elapsed,
    busy,
    legacyApi,
    apiPath,
    serverVersion,
    repoPath,
    repoLabel,
    timeoutSec,
    phase,
    scanMode,
    servedFromCache,
    staleAgeSec,
    refreshInBackground,
  } = useScanProgress(active, tab);
  const pct = busy ? Math.max(12, Math.min(98, progress)) : 100;
  const loggedRef = React.useRef(false);
  const expectedHint = timeoutSec != null ? `v2.5.0 / ${timeoutSec}s` : 'v2.5.0';

  React.useEffect(() => {
    if (!active) {
      loggedRef.current = false;
      return;
    }
    if (loggedRef.current) return;
    if (!repoPath && !repoLabel && timeoutSec == null) return;
    loggedRef.current = true;
    console.info(LOG, 'scan gestart', { tab, detail, repoLabel, repoPath });
  }, [active, tab, detail, repoLabel, repoPath, timeoutSec]);

  const scanTarget = repoLabel || repoPath;
  const phaseKey = phase || detail;

  return h(
    'div',
    {
      className:
        'codebase-viz-scan-progress' + (busy ? ' codebase-viz-scan-progress--busy' : ''),
      role: 'status',
      'aria-live': 'polite',
    },
    legacyApi
      ? h(
          'p',
          { className: 'codebase-viz-legacy-hint' },
          apiPath
            ? [
                'Verouderde plugin-backend (pygount stopt te vroeg). Geladen vanaf: ',
                h('code', { className: 'codebase-viz-api-path', key: 'api' }, apiPath),
                ' — verwijder of update die installatie, of start via ',
                h('code', { key: 'bat' }, 'start_hermes.bat'),
                ' en hard-refresh (Ctrl+Shift+R).',
              ]
            : [
                'Verouderde plugin-backend',
                serverVersion ? ` (v${serverVersion})` : '',
                ` — verwacht ${expectedHint}. Controleer `,
                h('code', { key: 'w1' }, '%LOCALAPPDATA%\\hermes\\plugins\\codebase-viz'),
                ' of ',
                h('code', { key: 'w2' }, '%USERPROFILE%\\.hermes\\plugins\\codebase-viz'),
                ', of voer ',
                h('code', { key: 'fix' }, 'start_hermes.bat'),
                ' uit en hard-refresh.',
              ],
        )
      : null,
    h(
      'div',
      {
        className: 'codebase-viz-progress-track',
        role: 'progressbar',
        'aria-valuemin': 0,
        'aria-valuemax': 100,
        'aria-valuenow': pct,
        'aria-label': detail,
      },
      h('div', {
        className: 'codebase-viz-progress-bar' + (busy && pct < 90 ? ' indeterminate' : ''),
        style: { width: `${pct}%` },
      }),
    ),
    h(
      'div',
      { className: 'codebase-viz-progress-meta', key: phaseKey },
      h('span', { className: 'codebase-viz-progress-detail' }, detail),
      elapsed
        ? h('span', { className: 'codebase-viz-progress-elapsed' }, elapsed)
        : busy
          ? h('span', { className: 'codebase-viz-progress-elapsed' }, '…')
          : null,
    ),
    h(
      'div',
      { className: 'codebase-viz-swr-meta' },
      scanMode ? h('span', { className: 'codebase-viz-swr-pill' }, `mode:${scanMode}`) : null,
      typeof servedFromCache === 'boolean'
        ? h(
            'span',
            { className: 'codebase-viz-swr-pill' },
            servedFromCache ? 'cached' : 'live',
          )
        : null,
      typeof staleAgeSec === 'number'
        ? h('span', { className: 'codebase-viz-swr-pill' }, `stale:${staleAgeSec}s`)
        : null,
      refreshInBackground
        ? h('span', { className: 'codebase-viz-swr-pill codebase-viz-swr-pill--active' }, 'refreshing')
        : null,
    ),
    scanTarget
      ? h(
          'p',
          {
            className: 'codebase-viz-scan-target',
            title: repoPath || scanTarget,
          },
          busy ? h('span', { className: 'codebase-viz-scan-pulse', 'aria-hidden': true }) : null,
          'Scan: ',
          h('code', null, scanTarget),
        )
      : null,
  );
}
