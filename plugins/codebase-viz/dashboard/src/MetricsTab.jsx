import React from 'react';
import { usePluginFetch } from './usePluginFetch';
import HistoryChart from './HistoryChart';

const h = React.createElement;

function ratioClass(ratio) {
  if (ratio >= 1 && ratio <= 3) return 'status-ok';
  if (ratio > 3) return 'status-warn';
  return 'status-err';
}

export default function MetricsTab({ data }) {
  if (!data) return null;

  const { data: history } = usePluginFetch('/history', []);
  const { Card, CardHeader, CardTitle, CardContent } =
    window.__HERMES_PLUGIN_SDK__.components;

  const langs = Object.entries(data.languages || {}).sort(
    (a, b) => (b[1].code || 0) - (a[1].code || 0),
  );

  return h(
    'div',
    { className: 'codebase-viz-metrics' },
    h(
      'div',
      { className: 'codebase-viz-metrics-grid' },
      h(MetricCard, { label: 'Total LOC', value: data.total_loc }),
      h(MetricCard, { label: 'Files', value: data.total_files }),
      h(MetricCard, { label: 'Languages', value: data.language_count }),
      h(MetricCard, {
        label: 'Prod : Test',
        value: `${data.ratio}:1`,
        valueClass: ratioClass(data.ratio),
      }),
    ),
    h(
      Card,
      null,
      h(CardHeader, null, h(CardTitle, null, 'Languages')),
      h(
        CardContent,
        null,
        h(
          'table',
          { className: 'codebase-viz-table' },
          h(
            'thead',
            null,
            h('tr', null, h('th', null, 'Language'), h('th', null, 'Files'), h('th', null, 'LOC')),
          ),
          h(
            'tbody',
            null,
            ...langs.map(([name, stats]) =>
              h(
                'tr',
                { key: name },
                h('td', null, name),
                h('td', null, stats.files),
                h('td', null, stats.code),
              ),
            ),
          ),
        ),
      ),
    ),
    history?.points?.length
      ? h(
          Card,
          null,
          h(CardHeader, null, h(CardTitle, null, 'LOC trend (commits)')),
          h(CardContent, null, h(HistoryChart, { data: history })),
        )
      : null,
    data.top_files?.length
      ? h(
          Card,
          null,
          h(CardHeader, null, h(CardTitle, null, 'Top files by LOC')),
          h(
            CardContent,
            null,
            h(
              'ul',
              { className: 'codebase-viz-list' },
              ...data.top_files.map((f) =>
                h('li', { key: f.path }, `${f.name} — ${f.loc} (${f.language || '?'})`),
              ),
            ),
          ),
        )
      : null,
  );
}

function MetricCard({ label, value, valueClass }) {
  const { Card, CardContent } = window.__HERMES_PLUGIN_SDK__.components;
  return h(
    Card,
    null,
    h(
      CardContent,
      { className: 'codebase-viz-metric-card' },
      h('div', { className: 'codebase-viz-metric-label' }, label),
      h('div', { className: `codebase-viz-metric-value ${valueClass || ''}` }, value),
    ),
  );
}
