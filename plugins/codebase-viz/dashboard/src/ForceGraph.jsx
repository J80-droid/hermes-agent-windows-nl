import React from 'react';
import {
  useFileWatcher,
  FileWatcherIndicator,
  useRippleAnimation,
} from './useFileWatcher';

const h = React.createElement;
const MAX_NODES = 500;

function pathToModuleId(filePath, nodeIds) {
  if (!filePath || !nodeIds?.length) return null;
  const norm = String(filePath).replace(/\\/g, '/');
  const base = norm.split('/').pop() || '';
  const stem = base.replace(/\.py$/i, '').replace(/\.__init__$/, '');
  const candidates = new Set([stem, stem.replace(/\//g, '.')]);
  for (const id of nodeIds) {
    if (candidates.has(id) || id.endsWith(`.${stem}`) || id.split('.').pop() === stem) {
      return id;
    }
  }
  return null;
}

function buildGraph(data, search) {
  const allEdges = Array.isArray(data?.edges) ? data.edges : [];
  const edges = search
    ? allEdges.filter(
        (e) =>
          e.source.toLowerCase().includes(search.toLowerCase()) ||
          e.target.toLowerCase().includes(search.toLowerCase()),
      )
    : allEdges;

  const nodeSet = new Set();
  edges.forEach((e) => {
    nodeSet.add(e.source);
    nodeSet.add(e.target);
  });

  let nodes = Array.from(nodeSet).map((id) => ({ id }));
  if (nodes.length > MAX_NODES) {
    const degree = {};
    edges.forEach((e) => {
      degree[e.source] = (degree[e.source] || 0) + 1;
      degree[e.target] = (degree[e.target] || 0) + 1;
    });
    nodes = nodes
      .sort((a, b) => (degree[b.id] || 0) - (degree[a.id] || 0))
      .slice(0, MAX_NODES);
    const allowed = new Set(nodes.map((n) => n.id));
    return {
      nodes,
      links: edges
        .filter((e) => allowed.has(e.source) && allowed.has(e.target))
        .map((e) => ({ source: e.source, target: e.target, type: e.type })),
      capped: true,
    };
  }

  return {
    nodes,
    links: edges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type,
    })),
    capped: false,
  };
}

export default function ForceGraph({ data }) {
  const svgRef = React.useRef(null);
  const containerRef = React.useRef(null);
  const simRef = React.useRef(null);
  const zoomBehaviorRef = React.useRef(null);
  const [search, setSearch] = React.useState('');
  const [inspector, setInspector] = React.useState(null);
  const [size, setSize] = React.useState({ w: 0, h: 0 });

  const { connected, lastEvent } = useFileWatcher();
  const ripple = useRippleAnimation(lastEvent);

  const graph = React.useMemo(() => buildGraph(data, search), [data, search]);

  React.useEffect(() => {
    const onEscape = () => setInspector(null);
    window.addEventListener('codebase-viz:escape', onEscape);
    return () => window.removeEventListener('codebase-viz:escape', onEscape);
  }, []);

  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    const ro = new ResizeObserver(() => {
      setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 400) });
    });
    ro.observe(container);
    setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 400) });
    return () => ro.disconnect();
  }, []);

  React.useEffect(() => {
    const svg = svgRef.current;
    if (!svg || !data?.nodes?.length || size.w < 10) return undefined;

    const d3 = window.d3;
    if (!d3) return undefined;

    const { nodes, links } = graph;
    if (!nodes.length) return undefined;

    const width = size.w;
    const height = size.h;
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.innerHTML = '';

    const g = d3.select(svg).append('g');
    const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', (event) => {
      g.attr('transform', event.transform);
    });
    zoomBehaviorRef.current = zoom;
    d3.select(svg).call(zoom);

    const simulation = d3
      .forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(20));

    simRef.current = simulation;

    const link = g
      .append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'hsl(var(--muted-foreground) / 0.3)')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', (d) => (d.type === 'from_import' ? '3,2' : '0'));

    const node = g
      .append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', 6)
      .attr('fill', 'hsl(var(--primary))')
      .attr('stroke', 'hsl(var(--border))')
      .attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .call(
        d3
          .drag()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      )
      .on('click', (_event, d) => setInspector(d.id))
      .on('mouseenter', function (_event, d) {
        if (d.x == null || d.y == null) return;
        g.append('circle')
          .attr('class', 'codebase-viz-hover-pulse')
          .attr('cx', d.x)
          .attr('cy', d.y)
          .attr('r', 6)
          .attr('fill', 'none')
          .attr('stroke', 'hsl(var(--primary))')
          .attr('stroke-width', 1.5)
          .attr('opacity', 0.85)
          .transition()
          .duration(450)
          .attr('r', 22)
          .attr('opacity', 0)
          .remove();
      });

    const label = g
      .append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text((d) => d.id.split('.').pop())
      .attr('font-size', '10px')
      .attr('dx', 8)
      .attr('dy', 3)
      .attr('fill', 'hsl(var(--foreground) / 0.8)');

    function drawRipplePulse() {
      if (!ripple?.path) return;
      const targetId = pathToModuleId(
        ripple.path,
        nodes.map((n) => n.id),
      );
      const target = targetId ? nodes.find((n) => n.id === targetId) : null;
      const cx = target?.x ?? width / 2;
      const cy = target?.y ?? height / 2;
      g.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', 6)
        .attr('fill', 'none')
        .attr('stroke', '#22c55e')
        .attr('stroke-width', 2)
        .transition()
        .duration(1000)
        .attr('r', 40)
        .attr('stroke-width', 0)
        .remove();
    }

    if (ripple?.path) {
      simulation.on('end', drawRipplePulse);
    }

    const flyToSearchMatch = () => {
      const q = search.trim().toLowerCase();
      if (!q || !zoomBehaviorRef.current) return;
      const match = nodes.find((n) => n.id.toLowerCase().includes(q));
      if (!match || match.x == null || match.y == null) return;
      const scale = 1.75;
      const transform = d3.zoomIdentity
        .translate(width / 2 - match.x * scale, height / 2 - match.y * scale)
        .scale(scale);
      d3.select(svg)
        .transition()
        .duration(650)
        .call(zoomBehaviorRef.current.transform, transform);
    };

    if (search.trim()) {
      simulation.on('end.fly', flyToSearchMatch);
      if (simulation.alpha() < 0.05) flyToSearchMatch();
    }

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);
      node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
      label.attr('x', (d) => d.x).attr('y', (d) => d.y);
    });

    return () => {
      simulation.on('end.fly', null);
      simulation.stop();
      simRef.current = null;
      zoomBehaviorRef.current = null;
    };
  }, [graph, ripple, size]);

  const edgeList = Array.isArray(data?.edges) ? data.edges : [];
  const inEdges = inspector
    ? edgeList.filter((e) => e.target === inspector).slice(0, 20)
    : [];
  const outEdges = inspector
    ? edgeList.filter((e) => e.source === inspector).slice(0, 20)
    : [];

  return h(
    'div',
    { style: { display: 'flex', flexDirection: 'column', height: '100%' } },
    h(
      'div',
      {
        style: {
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
          padding: '0.5rem 0',
          flexShrink: 0,
        },
      },
      h('input', {
        type: 'text',
        placeholder: 'Zoek module...',
        value: search,
        onChange: (e) => setSearch(e.target.value),
        style: {
          flex: 1,
          padding: '0.3rem 0.5rem',
          fontSize: '0.8rem',
          background: 'hsl(var(--input))',
          border: '1px solid hsl(var(--border))',
          borderRadius: '0.25rem',
          color: 'hsl(var(--foreground))',
        },
      }),
      h(FileWatcherIndicator, { connected }),
    ),
    graph.capped &&
      h(
        'p',
        { className: 'codebase-viz-hint', style: { margin: '0 0 0.25rem' } },
        `Grafiek beperkt tot ${MAX_NODES} modules (meest verbonden eerst).`,
      ),
    inspector &&
      h(
        'div',
        {
          className: 'codebase-viz-inspector',
          style: {
            padding: '0.5rem',
            background: 'hsl(var(--accent) / 0.2)',
            borderRadius: '0.25rem',
            fontSize: '0.8rem',
            marginBottom: '0.25rem',
            flexShrink: 0,
          },
        },
        h(
          'div',
          { style: { display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' } },
          h('strong', null, inspector),
          h(
            'button',
            {
              type: 'button',
              onClick: () => setInspector(null),
              style: {
                background: 'transparent',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.25rem',
                cursor: 'pointer',
                fontSize: '0.75rem',
                padding: '0.15rem 0.4rem',
              },
            },
            'Sluiten',
          ),
        ),
        h('div', null, h('span', { className: 'status-ok' }, 'Uit '), `${outEdges.length} imports`),
        outEdges.length > 0 &&
          h(
            'ul',
            { style: { margin: '0.2rem 0 0.4rem', paddingLeft: '1.2rem' } },
            outEdges.map((e) => h('li', { key: e.target + e.type }, e.target)),
          ),
        h('div', null, h('span', { className: 'status-err' }, 'In '), `${inEdges.length} imports`),
        inEdges.length > 0 &&
          h(
            'ul',
            { style: { margin: '0.2rem 0', paddingLeft: '1.2rem' } },
            inEdges.map((e) => h('li', { key: e.source + e.type }, e.source)),
          ),
      ),
    h('div', {
      ref: containerRef,
      style: { flex: 1, minHeight: 0, overflow: 'hidden' },
      children: h('svg', { ref: svgRef, style: { width: '100%', height: '100%' } }),
    }),
  );
}
