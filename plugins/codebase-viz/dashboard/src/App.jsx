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

  const isSearch = tab === 'search';
  const path = isSearch ? null : TAB_MAP[tab] || '/structure';
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

  if (tab === 'search') {
    return shell(h(SearchTab));
  }

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
        tab === 'sunburst' || tab === 'treemap'
          ? 'Scannen... (pygount)'
          : tab === 'force-graph'
            ? 'Analyseer imports...'
            : 'Laden...',
      ),
    );
  }

  if (tab === 'sunburst' && data.tree && !data.tree.children?.length) {
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

  return shell(content);
}
