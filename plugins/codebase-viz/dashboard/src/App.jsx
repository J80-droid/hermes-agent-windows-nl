import React from 'react';
import SunburstChart from './SunburstChart';
import MetricsTab from './MetricsTab';
import HealthTab from './HealthTab';
import ForceGraph from './ForceGraph';
import TreemapChart from './TreemapChart';
import { usePluginFetch, postForceScan, useD3Loader } from './usePluginFetch';

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
    id: 'hermes',
    label: 'Hermes',
    tabs: [{ id: 'health', label: 'Health' }],
  },
];

const TAB_MAP = {
  sunburst: '/structure',
  'force-graph': '/dependencies',
  treemap: '/structure',
  metrics: '/summary',
  health: '/doctor',
};

function CategoryNav({ categories, tab, setTab, menuOpen, setMenuOpen }) {
  return h(
    'div',
    { className: 'codebase-viz-tabs' },
    categories.map((cat) =>
      h(
        'div',
        {
          key: cat.id,
          className: 'codebase-viz-category' + (menuOpen === cat.id ? ' open' : ''),
          onMouseEnter: () => setMenuOpen(cat.id),
          onMouseLeave: () => setMenuOpen(null),
        },
        h('span', { className: 'codebase-viz-category-label' }, cat.label, ' \u25BE'),
        menuOpen === cat.id &&
          h(
            'div',
            { className: 'codebase-viz-dropdown' },
            cat.tabs.map((t) =>
              h(
                'button',
                {
                  key: t.id,
                  type: 'button',
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
  );
}

function parseFetchError(err) {
  if (!err) return 'Onbekende fout';
  const msg = String(err.message || err);
  const m = msg.match(/^\d{3}:\s*(.*)$/s);
  if (!m) return msg;
  try {
    const body = JSON.parse(m[1]);
    if (body && typeof body.detail === 'string') return body.detail;
  } catch (_e) { /* not JSON */ }
  return m[1] || msg;
}

export default function App() {
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK?.fetchJSON || !SDK?.components) {
    return h('div', { className: 'codebase-viz-error' }, 'Hermes Plugin SDK niet beschikbaar.');
  }
  const { Button } = SDK.components;
  const [tab, setTab] = React.useState('sunburst');
  const [menuOpen, setMenuOpen] = React.useState(null);
  const d3Ready = useD3Loader();

  const path = TAB_MAP[tab] || '/structure';
  const { data, error, loading } = usePluginFetch(path, [tab]);

  const currentCat = CATEGORIES.find((c) => c.tabs.some((t) => t.id === tab));
  const activeLabel = currentCat
    ? `${currentCat.label} \u203A ${currentCat.tabs.find((t) => t.id === tab)?.label}`
    : tab;

  const shell = (content) =>
    h(
      'div',
      { className: 'codebase-viz-container' },
      h(CategoryNav, { categories: CATEGORIES, tab, setTab, menuOpen, setMenuOpen }),
      h('div', { className: 'codebase-viz-active-label' }, activeLabel),
      h('div', { className: 'codebase-viz-content' }, content),
    );

  if (error || data?.fallback) {
    return shell(
      h(
        'div',
        { className: 'codebase-viz-error' },
        h('p', null, parseFetchError(error) || data?.error || 'Scan mislukt'),
        h(
          Button,
          {
            variant: 'outline',
            size: 'sm',
            onClick: () => postForceScan().then(() => window.location.reload()),
          },
          'Opnieuw proberen',
        ),
      ),
    );
  }

  if (loading || !data) {
    return shell(
      h(
        'p',
        { className: 'codebase-viz-loading' },
        tab === 'sunburst' || tab === 'treemap' ? 'Scannen... (pygount)' :
        tab === 'force-graph' ? 'Analyseer imports...' : 'Laden...',
      ),
    );
  }

  if (
    tab === 'sunburst' &&
    data.tree &&
    !data.tree.children?.length
  ) {
    return shell(
      h(
        'div',
        { className: 'codebase-viz-empty' },
        h('p', null, 'Geen bestanden gevonden in de repo.'),
        h(
          'p',
          { className: 'codebase-viz-hint' },
          'Zet CODEBASE_VIZ_REPO naar je git-root en herstart het dashboard.',
        ),
      ),
    );
  }

  let content;
  switch (tab) {
    case 'sunburst':
      if (!d3Ready) {
        content = h('p', { className: 'codebase-viz-loading' }, 'D3 laden...');
      } else {
        content = h(SunburstChart, { data });
      }
      break;
    case 'force-graph':
      if (!d3Ready) {
        content = h('p', { className: 'codebase-viz-loading' }, 'D3 laden...');
      } else if (!data.nodes?.length) {
        content = h('p', { className: 'codebase-viz-empty' }, 'Geen Python modules gevonden om te analyseren.');
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
    default:
      content = h('p', null, 'Tab nog niet geïmplementeerd.');
  }

  return shell(content);
}