import React from 'react';

const h = React.createElement;

export default function TimelineTab({ data }) {
  const frames = data?.frames || [];
  if (!frames.length) {
    return h('p', { className: 'codebase-viz-empty' }, 'Geen commit-geschiedenis.');
  }
  return h(
    'div',
    { className: 'codebase-viz-timeline' },
    h('p', { className: 'codebase-viz-hint' }, `${frames.length} commits (oud → nieuw)`),
    h(
      'ol',
      { style: { fontSize: '0.8rem', maxHeight: '70vh', overflow: 'auto', paddingLeft: '1.2rem' } },
      ...frames.map((f) =>
        h('li', { key: f.sha + f.date, style: { marginBottom: '0.35rem' } },
          h('code', null, f.sha), ' — ', f.date, ' — ', f.message),
      ),
    ),
  );
}
