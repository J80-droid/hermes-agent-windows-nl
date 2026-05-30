import React from 'react';

const h = React.createElement;

const LANG_COLORS = {
  python: '#4CAF50',
  javascript: '#FFD54F',
  typescript: '#64B5F6',
  jsx: '#81D4FA',
  tsx: '#64B5F6',
  markdown: '#90CAF9',
  json: '#BDBDBD',
  yaml: '#A5D6A7',
  html: '#FFAB91',
  css: '#80DEEA',
  shell: '#AED581',
  powershell: '#90A4AE',
  sql: '#FFB74D',
  dockerfile: '#4FC3F7',
  makefile: '#C5E1A5',
  rust: '#FFCC80',
  go: '#4DD0E1',
  'c#': '#A5D6A7',
  ruby: '#EF9A9A',
  php: '#CE93D8',
  java: '#FFB74D',
  kotlin: '#B39DDB',
  scala: '#EF9A9A',
  swift: '#FFAB91',
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

function textColorForBackground(hex) {
  if (!hex || hex.startsWith('hsl')) return '#fff';
  const r = parseInt(hex.slice(1, 3), 16) || 0;
  const g = parseInt(hex.slice(3, 5), 16) || 0;
  const b = parseInt(hex.slice(5, 7), 16) || 0;
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.55 ? '#0f0f0f' : '#ffffff';
}

export default function TreemapChart({ data }) {
  const svgRef = React.useRef(null);
  const containerRef = React.useRef(null);
  const [zoomStack, setZoomStack] = React.useState([]);
  const [size, setSize] = React.useState({ w: 0, h: 0 });
  const [tooltip, setTooltip] = React.useState(null);
  const tooltipRef = React.useRef(null);

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
    if (!container) return undefined;
    const ro = new ResizeObserver(() => {
      setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 300) });
    });
    ro.observe(container);
    setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 300) });
    return () => ro.disconnect();
  }, []);

  React.useEffect(() => {
    const svg = svgRef.current;
    if (!svg || size.w < 10) return undefined;

    const d3 = window.d3;
    if (!d3) return undefined;

    const width = size.w;
    const height = size.h;
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

    const cellSel = g.selectAll('g.cell')
      .data(cells)
      .join('g')
      .attr('class', 'cell');

    cellSel.append('rect')
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
      .on('mousemove', function(event, d) {
        event.stopPropagation();
        const kind = d.data.type === 'dir' ? 'map' : (d.data.language || '?');
        setTooltip({
          x: event.clientX + 12,
          y: event.clientY - 8,
          html: `<strong>${d.data.name}</strong><br/>${kind}<br/>${d.value} LOC`,
        });
      })
      .on('mouseleave', function() {
        setTooltip(null);
      });

    cellSel.append('text')
      .attr('class', 'label')
      .attr('x', (d) => d.x0 + 3)
      .attr('y', (d) => d.y0 + 12)
      .attr('font-size', (d) => {
        const h = d.y1 - d.y0;
        if (h < 14) return '0px';
        return Math.min(12, Math.max(9, h / 3.5)) + 'px';
      })
      .attr('fill', (d) => {
        if (d.data.type === 'dir') return 'hsl(var(--foreground))';
        return textColorForBackground(getColor(d.data.language, d3));
      })
      .style('pointer-events', 'none')
      .style('text-shadow', (d) =>
        d.data.type === 'dir' ? 'none' : '0 1px 2px rgba(0,0,0,0.35)',
      )
      .style('opacity', (d) => {
        const area = (d.x1 - d.x0) * (d.y1 - d.y0);
        return area < 200 ? 0 : 1;
      })
      .each(function(d) {
        const w = d.x1 - d.x0;
        const h = d.y1 - d.y0;
        if (w < 24 || h < 14) {
          d3.select(this).text('');
          return;
        }
        const label = d.data.type === 'dir' ? `${d.data.name}/` : d.data.name;
        const maxChars = Math.floor((w - 6) / (label.length > 10 ? 5.5 : 6));
        const text = label.length > maxChars && maxChars > 0
          ? label.substring(0, maxChars) + '…'
          : label;
        d3.select(this).text(text);
      });

    return undefined;
  }, [currentData, size]);

  const crumbs = zoomStack.length ? zoomStack : [treeData];

  return h(
    'div',
    { style: { display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' } },
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
        '\u2190 Terug',
      ),
      crumbs.map((node, i) =>
        h(
          'span',
          { key: `${node.path || node.name}-${i}`, style: { color: 'hsl(var(--muted-foreground))' } },
          i === 0 ? '' : ' \u203A ',
          node.name || 'root',
        ),
      ),
    ),
    h('div', {
      ref: containerRef,
      style: { flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' },
      children: h('svg', { ref: svgRef, style: { width: '100%', height: '100%', display: 'block' } }),
    }),
    tooltip && h('div', {
      ref: tooltipRef,
      style: {
        position: 'fixed',
        left: tooltip.x,
        top: tooltip.y,
        background: 'hsl(var(--popover, var(--background)))',
        color: 'hsl(var(--popover-foreground, var(--foreground)))',
        border: '1px solid hsl(var(--border))',
        borderRadius: '0.4rem',
        padding: '0.35rem 0.6rem',
        fontSize: '0.78rem',
        lineHeight: 1.4,
        pointerEvents: 'none',
        boxShadow: '0 4px 16px rgba(0,0,0,0.35)',
        zIndex: 2000,
        maxWidth: '16rem',
      },
      dangerouslySetInnerHTML: { __html: tooltip.html },
    }),
  );
}
