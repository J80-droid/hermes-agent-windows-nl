import React from 'react';

const h = React.createElement;

/**
 * Generic table for Sprint 3 endpoints returning { items: [...] }.
 */
export default function DataTableTab({ data, columns, title, hint }) {
  const { Card, CardHeader, CardTitle, CardContent } =
    window.__HERMES_PLUGIN_SDK__.components;

  const items = data?.items || data?.frames || data?.points || [];
  const err = data?.error;

  if (err && !items.length) {
    return h('div', { className: 'codebase-viz-empty' }, h('p', null, err));
  }

  if (!items.length) {
    return h('div', { className: 'codebase-viz-empty' }, h('p', null, 'Geen resultaten.'));
  }

  return h(
    'div',
    { className: 'codebase-viz-table-tab' },
    hint && h('p', { className: 'codebase-viz-hint' }, hint),
    data?.coverage_pct != null &&
      h('p', null, `Geschatte dekking: ${data.coverage_pct}% (${data.covered}/${data.total})`),
    data?.total != null && h('p', { className: 'codebase-viz-hint' }, `Totaal: ${data.total}`),
    h(
      Card,
      null,
      h(CardHeader, null, h(CardTitle, null, title || 'Resultaten')),
      h(
        CardContent,
        null,
        h(
          'div',
          { className: 'codebase-viz-virtual-scroll' },
          h(
            'table',
            { className: 'codebase-viz-table' },
            h(
              'thead',
              null,
              h('tr', null, ...columns.map((c) => h('th', { key: c.key }, c.label))),
            ),
            h(
              'tbody',
              null,
              ...items.map((row, i) =>
                h(
                  'tr',
                  { key: row.file || row.module || row.author || row.sha || i },
                  ...columns.map((c) =>
                    h('td', { key: c.key }, c.render ? c.render(row) : String(row[c.key] ?? '')),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
