import React from 'react';
import { usePluginFetch } from './usePluginFetch';
import DataTableTab from './DataTableTab';

const h = React.createElement;

export default function SearchTab() {
  const [query, setQuery] = React.useState('');
  const path = query.length >= 2 ? `/search?q=${encodeURIComponent(query)}` : null;
  const { data, error, loading } = usePluginFetch(path, [query]);

  return h(
    'div',
    null,
    h('input', {
      type: 'search',
      placeholder: 'Zoek in codebase (min. 2 tekens)...',
      value: query,
      onChange: (e) => setQuery(e.target.value),
      style: {
        width: '100%',
        padding: '0.5rem',
        marginBottom: '0.75rem',
        fontSize: '0.85rem',
        borderRadius: '0.25rem',
        border: '1px solid hsl(var(--border))',
        background: 'hsl(var(--input))',
        color: 'hsl(var(--foreground))',
      },
    }),
    query.length < 2 && h('p', { className: 'codebase-viz-hint' }, 'Typ minimaal 2 tekens.'),
    loading && query.length >= 2 && h('p', { className: 'codebase-viz-loading' }, 'Zoeken...'),
    error && h('p', { className: 'codebase-viz-error' }, error.message || 'Zoekfout'),
    data &&
      h(DataTableTab, {
        data,
        title: `Zoekresultaten voor "${query}"`,
        columns: [
          { key: 'file', label: 'Bestand' },
          { key: 'line', label: 'Regel' },
          { key: 'text', label: 'Context' },
        ],
      }),
  );
}
