import React from 'react';

const h = React.createElement;

const LANG_COLORS = {
  python: '#3776AB',
  javascript: '#F7DF1E',
  typescript: '#3178C6',
  jsx: '#61DAFB',
  tsx: '#3178C6',
  markdown: '#083FA1',
  json: '#292929',
  yaml: '#6CB2E6',
  html: '#E34F26',
  css: '#1572B6',
  shell: '#4EAA25',
  powershell: '#012456',
  sql: '#E38C00',
  dockerfile: '#2496ED',
  makefile: '#427819',
  rust: '#DEA584',
  go: '#00ADD8',
  'c#': '#178600',
  ruby: '#CC342D',
  php: '#777BB4',
  java: '#ED8B00',
  kotlin: '#7F52FF',
  scala: '#DC322F',
  swift: '#F05138',
};

function subtreeLoc(node) {
  if (!node) return 0;
  if (node.type === 'file') return node.loc || 0;
  return (node.children || []).reduce((sum, ch) => sum + subtreeLoc(ch), 0);
}

function getColor(lang, d3) {
  if (!lang) return 'hsl(var(--primary))';
  const base = LANG_COLORS[lang.toLowerCase()];
  if (base) return base;
  if (!d3) return 'hsl(var(--primary))';
  const hue = lang.split('').reduce((a, c) => a + c.charCodeAt(0), 0) * 13.7 % 360;
  return d3.hsl(hue, 0.5, 0.5).formatHex();
}

function immediateChildren(treeNode) {
  return (treeNode.children || [])
    .map((c) => ({
      name: c.name,
      type: c.type,
      language: c.language,
      loc: c.type === 'file' ? (c.loc || 0) : subtreeLoc(c),
      children: c.children,
      _raw: c,
    }))
    .filter((c) => c.loc > 0);
}

export default function TreemapChart({ data }) {
  const svgRef = React.useRef(null);
  const containerRef = React.useRef(null);
  const [zoomStack, setZoomStack] = React.useState([]);

  const treeData = data?.tree || { name: 'root', children: [], loc: 0 };
  const currentData =
    zoomStack.length > 0 ? zoomStack[zoomStack.length - 1] : treeData;

  function zoomTo(node) {
    setZoomStack((prev) => [...prev, node]);
  }

  function zoomOut() {
    setZoomStack((prev) => (prev.length > 1 ? prev.slice(0, -1) : []));
  }

  React.useEffect(() => {
    const container = containerRef.current;
    const svg = svgRef.current;
    if (!container || !svg) return undefined;

    const d3 = window.d3;
    if (!d3) return undefined;

    const width = container.clientWidth;
    const height = Math.max(container.clientHeight, 400);
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.innerHTML = '';

    const items = immediateChildren(currentData);
    if (!items.length) {
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', String(width / 2));
      label.setAttribute('y', String(height / 2));
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('fill', 'hsl(var(--muted-foreground))');
      label.setAttribute('font-size', '14');
      label.textContent = 'Geen data voor deze directory';
      svg.appendChild(label);
      return undefined;
    }

    const root = d3
      .hierarchy({ name: 'root', children: items })
      .sum((d) => d.loc || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0));

    d3
      .treemap()
      .size([width, height])
      .paddingOuter(2)
      .paddingInner(1)
      .round(true)(root);

    const cells = root.children || [];
    if (!cells.length) return undefined;

    const g = d3.select(svg).append('g');

    g.selectAll('rect')
      .data(cells)
      .join('rect')
      .attr('x', (d) => d.x0)
      .attr('y', (d) => d.y0)
      .attr('width', (d) => Math.max(0, d.x1 - d.x0))
      .attr('height', (d) => Math.max(0, d.y1 - d.y0))
      .attr('fill', (d) =>
        d.data.type === 'dir'
          ? 'hsl(var(--muted-foreground) / 0.25)'
          : getColor(d.data.language, d3),
      )
      .attr('stroke', 'hsl(var(--background))')
      .attr('stroke-width', 1)
      .style('cursor', (d) =>
        d.data.type === 'dir' && d.data._raw?.children?.length ? 'pointer' : 'default',
      )
      .on('click', (_event, d) => {
        if (d.data.type === 'dir' && d.data._raw?.children?.length) {
          zoomTo(d.data._raw);
        }
      })
      .append('title')
      .text((d) => {
        const kind = d.data.type === 'dir' ? 'map' : d.data.language || '?';
        return `${d.data.name}\n${kind}\n${d.value} LOC`;
      });

    g.selectAll('text.label')
      .data(cells)
      .join('text')
      .attr('class', 'label')
      .attr('x', (d) => d.x0 + 3)
      .attr('y', (d) => d.y0 + 12)
      .attr('font-size', '10px')
      .attr('fill', (d) => (d.data.type === 'dir' ? 'hsl(var(--foreground))' : '#fff'))
      .style('pointer-events', 'none')
      .style('text-shadow', (d) =>
        d.data.type === 'dir' ? 'none' : '0 1px 2px rgba(0,0,0,0.6)',
      )
      .text((d) => {
        const w = d.x1 - d.x0;
        if (w < 40) return '';
        const label =
          d.data.type === 'dir' ? `${d.data.name}/` : d.data.name;
        return label.length * 7 > w
          ? `${label.substring(0, Math.floor(w / 7))}…`
          : label;
      })
      .style('opacity', (d) => {
        const area = (d.x1 - d.x0) * (d.y1 - d.y0);
        return area < 600 ? 0 : 1;
      });

    return undefined;
  }, [currentData]);

  const crumbs = zoomStack.length ? zoomStack : [treeData];

  return h(
    'div',
    { style: { display: 'flex', flexDirection: 'column', height: '100%' } },
    h(
      'div',
      {
        style: {
          display: 'flex',
          gap: '0.25rem',
          alignItems: 'center',
          padding: '0.5rem 0',
          flexShrink: 0,
          fontSize: '0.8rem',
          flexWrap: 'wrap',
        },
      },
      h(
        'button',
        {
          type: 'button',
          onClick: zoomOut,
          disabled: !zoomStack.length,
          style: {
            background: 'transparent',
            border: '1px solid hsl(var(--border))',
            borderRadius: '0.25rem',
            cursor: zoomStack.length ? 'pointer' : 'default',
            fontSize: '0.75rem',
            padding: '0.15rem 0.4rem',
            opacity: zoomStack.length ? 1 : 0.4,
          },
        },
        '← Terug',
      ),
      crumbs.map((node, i) =>
        h(
          'span',
          { key: `${node.path || node.name}-${i}`, style: { color: 'hsl(var(--muted-foreground))' } },
          i === 0 ? '' : ' › ',
          node.name || 'root',
        ),
      ),
    ),
    h('div', {
      ref: containerRef,
      style: { flex: 1, minHeight: 0, overflow: 'hidden' },
      children: h('svg', { ref: svgRef, style: { width: '100%', height: '100%' } }),
    }),
  );
}
