import React from 'react';
import { postForceScan } from './usePluginFetch';

const h = React.createElement;

function StatusBadge({ status }) {
  if (status === 'error') return h('span', { className: 'status-err' }, 'Error');
  if (status === 'warning') return h('span', { className: 'status-warn' }, 'Warning');
  return h('span', { className: 'status-ok' }, 'OK');
}

function HealthSection({ section }) {
  const errors = section.checks.filter((c) => c.status === 'error');
  const warnings = section.checks.filter((c) => c.status === 'warning');

  return h(
    'div',
    { className: 'codebase-viz-health-section' },
    h('div', { className: 'codebase-viz-health-section-title' }, section.name),
    ...errors.map((c) =>
      h('div', { key: c.text, className: 'codebase-viz-health-line' },
        h(StatusBadge, { status: 'error' }),
        ' ',
        c.text,
      ),
    ),
    ...warnings.map((c) =>
      h('div', { key: c.text, className: 'codebase-viz-health-line' },
        h(StatusBadge, { status: 'warning' }),
        ' ',
        c.text,
      ),
    ),
  );
}

export default function HealthTab({ data }) {
  if (!data?.sections) {
    return h('p', null, data?.error || 'Geen doctor-data.');
  }

  const { Button } = window.__HERMES_PLUGIN_SDK__.components;
  const { summary } = data;
  const score = summary?.score || 0;
  const overallClass =
    score >= 90 ? 'status-ok' : score >= 70 ? 'status-warn' : 'status-err';

  return h(
    'div',
    { className: 'codebase-viz-health' },
    h(
      'div',
      { className: 'codebase-viz-health-header' },
      h('span', { className: overallClass }, `Health: ${summary.overall}`),
      ` (${score}%) — `,
      h('span', { className: 'status-ok' }, `${summary.ok} OK`),
      ' ',
      h('span', { className: 'status-warn' }, `${summary.warnings} warnings`),
      ' ',
      h('span', { className: 'status-err' }, `${summary.errors} errors`),
      h(
        Button,
        {
          variant: 'outline',
          size: 'sm',
          style: { marginLeft: '1rem' },
          onClick: () => postForceScan().then(() => window.location.reload()),
        },
        'Refresh',
      ),
    ),
    h(
      'div',
      { className: 'codebase-viz-health-grid' },
      ...data.sections.map((section) =>
        h(HealthSection, { key: section.name, section }),
      ),
    ),
    h(
      'details',
      { style: { marginTop: '1rem' } },
      h('summary', null, 'Raw doctor output'),
      h('pre', { className: 'codebase-viz-raw' }, data.raw),
    ),
  );
}
