import React from 'react';
import SunburstChart from './SunburstChart';
import MetricsTab from './MetricsTab';
import HealthTab from './HealthTab';
import ForceGraph from './ForceGraph';
import TreemapChart from './TreemapChart';
import DataTableTab from './DataTableTab';
import SearchTab from './SearchTab';
import TimelineTab from './TimelineTab';
import { usePluginFetch, postForceScan, useD3Loader } from './usePluginFetch';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';
import ScanProgress from './ScanProgress';

const h = React.createElement;

const CATEGORIES = [
  {
    id: 'visuals',
    label: 'Visuals',
    tabs: [
      { id: 'sunburst', label: 'Sunburst' },
      { id: 'force-graph', label: 'Force Graph' },
      { id: 'treemap', label: 'Treemap' },
      { id: 'metrics', label: 'Metrics' },
    ],
  },
  {
    id: 'analysis',
    label: 'Analysis',
    tabs: [
      { id: 'churn', label: 'Churn' },
      { id: 'age-map', label: 'Age Map' },
      { id: 'complexity', label: 'Complexity' },
      { id: 'todos', label: 'TODO/FIXME' },
      { id: 'blame', label: 'Blame' },
      { id: 'coverage', label: 'Coverage' },
      { id: 'dead-imports', label: 'Dead Imports' },
    ],
  },
  {
    id: 'hermes',
    label: 'Hermes',
    tabs: [
      { id: 'health', label: 'Health' },
      { id: 'config-drift', label: 'Config Drift' },
      { id: 'session-stats', label: 'Session Stats' },
    ],
  },
  {
    id: 'tools',
    label: 'Tools',
    tabs: [
      { id: 'search', label: 'Search' },
      { id: 'timeline', label: 'Timeline' },
    ],
  },
];

const TAB_MAP = {
  sunburst: '/structure',
  'force-graph': '/dependencies',
  treemap: '/structure',
  metrics: '/summary',
  churn: '/churn',
  'age-map': '/age-map',
  complexity: '/complexity',
  todos: '/todos',
  blame: '/blame',
  coverage: '/coverage',
  'dead-imports': '/dead-imports',
  health: '/doctor',
  'config-drift': '/config-drift',
  'session-stats': '/session-stats',
  timeline: '/timeline',
};

const TABLE_TABS = {
  churn: {
    title: 'Churn (laatste jaar)',
    columns: [
      { key: 'file', label: 'Bestand' },
      { key: 'commits', label: 'Commits' },
    ],
  },
  'age-map': {
    title: 'Age map',
    columns: [
      { key: 'file', label: 'Bestand' },
      { key: 'last_modified', label: 'Laatst gewijzigd' },
      { key: 'loc', label: 'LOC' },
    ],
  },
  complexity: {
    title: 'Complexity (radon)',
    columns: [
      { key: 'file', label: 'Bestand' },
      { key: 'avg_complexity', label: 'Gem.' },
      { key: 'max', label: 'Max' },
      { key: 'blocks', label: 'Blocks' },
    ],
  },
  todos: {
    title: 'TODO / FIXME',
    columns: [
      { key: 'file', label: 'Bestand' },
      { key: 'todo', label: 'TODO' },
      { key: 'fixme', label: 'FIXME' },
      { key: 'total', label: 'Totaal' },
    ],
  },
  blame: {
    title: 'Contributors',
    columns: [
      { key: 'author', label: 'Auteur' },
      { key: 'commits', label: 'Commits' },
    ],
  },
  coverage: {
    title: 'Test coverage (indicatief)',
    columns: [
      { key: 'module', label: 'Module' },
      {
        key: 'has_test',
        label: 'Test',
        render: (r) => (r.has_test ? 'ja' : 'nee'),
      },
    ],
  },
  'dead-imports': {
    title: 'Modules zonder inkomende imports',
    columns: [
      { key: 'module', label: 'Module' },
      { key: 'incoming', label: 'Incoming' },
    ],
  },
  'config-drift': {
    title: 'Config bestanden',
    columns: [
      { key: 'path', label: 'Pad' },
      { key: 'size', label: 'Bytes' },
    ],
  },
  'session-stats': {
    title: 'Session DB',
    columns: [
      { key: 'table', label: 'Tabel' },
      { key: 'rows', label: 'Rijen' },
    ],
  },
};

function CategoryNav({ categories, tab, setTab, menuOpen, setMenuOpen }) {
  const navRef = React.useRef(null);

  React.useEffect(() => {
    if (!menuOpen) return undefined;
    function onKey(e) {
      if (e.key === 'Escape') setMenuOpen(null);
    }
    function onPointerDown(e) {
      const root = navRef.current;
      if (!root || root.contains(e.target)) return;
      setMenuOpen(null);
    }
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, [menuOpen, setMenuOpen]);

  return h(
    'div',
    {
      ref: navRef,
      className: 'codebase-viz-nav-shell' + (menuOpen ? ' is-menu-open' : ''),
    },
    h(
      'div',
      { className: 'codebase-viz-tabs', role: 'menubar' },
      categories.map((cat) =>
        h(
          'div',
          {
            key: cat.id,
            className: 'codebase-viz-category' + (menuOpen === cat.id ? ' open' : ''),
            role: 'none',
          },
          h(
            'button',
            {
              type: 'button',
              className: 'codebase-viz-category-trigger',
              'aria-expanded': menuOpen === cat.id,
              'aria-haspopup': 'menu',
              onClick: () => setMenuOpen(menuOpen === cat.id ? null : cat.id),
            },
            cat.label,
            ' \u25BE',
          ),
          menuOpen === cat.id &&
            h(
              'div',
              { className: 'codebase-viz-dropdown', role: 'menu' },
              cat.tabs.map((t) =>
                h(
                  'button',
                  {
                    key: t.id,
                    type: 'button',
                    role: 'menuitem',
                    className:
                      'codebase-viz-dropdown-item' + (tab === t.id ? ' active' : ''),
                    onClick: () => {
                      setTab(t.id);
                      setMenuOpen(null);
                    },
                  },
                  t.label,
                ),
              ),
            ),
        ),
      ),
    ),
  );
}

function parseFetchError(err) {
  if (!err) return '';
  const msg = String(err.message || err.name || err);
  if (!msg || msg === '[object Object]') {
    try {
      return JSON.stringify(err);
    } catch (_e) {
      return 'Netwerkfout — open DevTools → Network';
    }
  }
  const m = msg.match(/^\d{3}:\s*(.*)$/s);
  if (!m) return msg;
  try {
    const body = JSON.parse(m[1]);
    if (body && typeof body.detail === 'string') return body.detail;
    if (body && typeof body.error === 'string') return body.error;
  } catch (_e) { /* not JSON */ }
  return m[1] || msg;
}

function WarningBanner({ message, onRetry }) {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const { Button } = SDK?.components || {};
  return h(
    'div',
    { className: 'codebase-viz-warn-banner', role: 'alert' },
    h('p', null, message),
    Button &&
      h(
        Button,
        { variant: 'outline', size: 'sm', onClick: onRetry },
        'Opnieuw proberen',
      ),
  );
}

export default function App() {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK?.fetchJSON || !SDK?.components) {
    return h('div', { className: 'codebase-viz-error' }, 'Hermes Plugin SDK niet beschikbaar.');
  }
  const { Button } = SDK.components;
  const [tab, setTab] = React.useState('sunburst');
  const [menuOpen, setMenuOpen] = React.useState(null);
  const [refreshToken, setRefreshToken] = React.useState(0);
  const d3Ready = useD3Loader();

  const onRefresh = React.useCallback(() => {
    postForceScan()
      .catch(() => {})
      .finally(() => setRefreshToken((n) => n + 1));
  }, []);

  useKeyboardShortcuts({ setTab, onRefresh });

  const isSearch = tab === 'search';
  const path = isSearch ? null : TAB_MAP[tab] || '/structure';
  const { data, error, loading } = usePluginFetch(path, [tab], refreshToken);

  const currentCat = CATEGORIES.find((c) => c.tabs.some((t) => t.id === tab));
  const activeLabel = currentCat
    ? `${currentCat.label} \u203A ${currentCat.tabs.find((t) => t.id === tab)?.label}`
    : tab;

  const shell = (content) =>
    h(
      'div',
      { className: 'codebase-viz-container' },
      h(CategoryNav, { categories: CATEGORIES, tab, setTab, menuOpen, setMenuOpen }),
      !menuOpen &&
        h(
          'div',
          { className: 'codebase-viz-active-label', 'aria-live': 'polite' },
          activeLabel,
        ),
      h('div', { className: 'codebase-viz-content' }, content),
      h(
        'div',
        { className: 'codebase-viz-shortcuts-hint', title: 'Sneltoetsen' },
        '1–9 tabs · 0 coverage · r ververs · Esc sluit inspector',
      ),
    );

  if (tab === 'search') {
    return shell(h(SearchTab));
  }

  if (error) {
    return shell(
      h(
        'div',
        { className: 'codebase-viz-error' },
        h('p', null, parseFetchError(error) || 'Scan mislukt (netwerk of server)'),
        h(
          Button,
          {
            variant: 'outline',
            size: 'sm',
            onClick: onRefresh,
          },
          'Opnieuw proberen',
        ),
      ),
    );
  }

  if (loading || !data) {
    return shell(
      h(
        'div',
        { className: 'codebase-viz-loading-panel' },
        h(ScanProgress, { active: true, tab }),
      ),
    );
  }

  if (tab === 'sunburst' && data.tree && !data.tree.children?.length) {
    return shell(
      h(
        'div',
        { className: 'codebase-viz-empty' },
        data?.error &&
          h(WarningBanner, { message: data.error, onRetry: onRefresh }),
        h(
          'p',
          null,
          data?.error
            ? 'Scan afgebroken of geen resultaat.'
            : 'Geen bestanden gevonden in de repo.',
        ),
        !data?.error &&
          h(
            'p',
            { className: 'codebase-viz-hint' },
            'Zet CODEBASE_VIZ_REPO naar je git-root en herstart het dashboard.',
          ),
      ),
    );
  }

  const warnMsg = data?.error || (data?.fallback ? 'Gedeeltelijke data (fallback)' : null);

  let content;
  switch (tab) {
    case 'sunburst':
      content = !d3Ready
        ? h('p', { className: 'codebase-viz-loading' }, 'D3 laden...')
        : h(SunburstChart, { data });
      break;
    case 'force-graph':
      if (!d3Ready) {
        content = h('p', { className: 'codebase-viz-loading' }, 'D3 laden...');
      } else if (!data.nodes?.length) {
        content = h('p', { className: 'codebase-viz-empty' }, 'Geen Python modules gevonden.');
      } else {
        content = h(ForceGraph, { data });
      }
      break;
    case 'treemap':
      if (!d3Ready) {
        content = h('p', { className: 'codebase-viz-loading' }, 'D3 laden...');
      } else if (!data.tree?.children?.length) {
        content = h('p', { className: 'codebase-viz-empty' }, 'Geen bestanden voor treemap.');
      } else {
        content = h(TreemapChart, { data });
      }
      break;
    case 'metrics':
      content = h(MetricsTab, { data });
      break;
    case 'health':
      content = h(HealthTab, { data });
      break;
    case 'timeline':
      content = h(TimelineTab, { data });
      break;
    default: {
      const spec = TABLE_TABS[tab];
      if (spec) {
        content = h(DataTableTab, {
          data,
          title: spec.title,
          columns: spec.columns,
        });
      } else {
        content = h('p', null, 'Tab nog niet geïmplementeerd.');
      }
    }
  }

  return shell(
    h(
      'div',
      { className: 'codebase-viz-tab-body' },
      warnMsg && h(WarningBanner, { message: warnMsg, onRetry: onRefresh }),
      content,
    ),
  );
}
