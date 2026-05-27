import React from 'react';
import { useScanProgress } from './useScanProgress';

const h = React.createElement;
const LOG = '[codebase-viz]';

export default function ScanProgress({ active, tab }) {
  const { detail, progress, elapsed, busy, legacyApi, apiPath, serverVersion } =
    useScanProgress(active, tab);
  const pct = busy ? Math.max(12, Math.min(98, progress)) : 100;
  const loggedRef = React.useRef(false);

  React.useEffect(() => {
    if (active && !loggedRef.current) {
      loggedRef.current = true;
      console.info(LOG, 'scan gestart', { tab, detail });
    }
    if (!active) loggedRef.current = false;
  }, [active, tab, detail]);

  return h(
    'div',
    { className: 'codebase-viz-scan-progress', role: 'status', 'aria-live': 'polite' },
    legacyApi
      ? h(
          'p',
          { className: 'codebase-viz-legacy-hint' },
          apiPath
            ? [
                'Verouderde plugin-backend (pygount stopt na 30s). Geladen vanaf: ',
                h('code', { className: 'codebase-viz-api-path', key: 'api' }, apiPath),
                ' — verwijder of update die installatie, of start via ',
                h('code', { key: 'bat' }, 'start_hermes.bat'),
                ' en hard-refresh (Ctrl+Shift+R).',
              ]
            : [
                'Verouderde plugin-backend',
                serverVersion ? ` (v${serverVersion})` : '',
                ' — pygount stopt na 30s (verwacht v2.5.0 / 120s). Controleer ',
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
      { className: 'codebase-viz-progress-meta' },
      h('span', { className: 'codebase-viz-progress-detail' }, detail),
      elapsed
        ? h('span', { className: 'codebase-viz-progress-elapsed' }, `${elapsed}`)
        : busy
          ? h('span', { className: 'codebase-viz-progress-elapsed' }, '…')
          : null,
    ),
  );
}
