import React, { useEffect, useRef, useState } from 'react';

const COLOR_MAP = {
  Python: '#4CAF50',
  TypeScript: '#64B5F6',
  JavaScript: '#FFD54F',
  HTML: '#FFAB91',
  CSS: '#80DEEA',
  Shell: '#AED581',
  Markdown: '#90CAF9',
  YAML: '#A5D6A7',
  JSON: '#BDBDBD',
  Dockerfile: '#4FC3F7',
};
const COLOR_DEFAULT = '#90A4AE';

function textColorForBackground(hex) {
  if (!hex || hex.startsWith('hsl')) return '#fff';
  const r = parseInt(hex.slice(1, 3), 16) || 0;
  const g = parseInt(hex.slice(3, 5), 16) || 0;
  const b = parseInt(hex.slice(5, 7), 16) || 0;
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.55 ? '#0f0f0f' : '#ffffff';
}

function centroidLabel(d) {
  const r = (d.y0 + d.y1) / 2;
  const a = (d.x0 + d.x1) / 2 - Math.PI / 2;
  return {
    x: r * Math.cos(a),
    y: r * Math.sin(a),
    rotation: (a * 180) / Math.PI + (a > Math.PI / 2 ? 180 : 0),
    anchor: a > Math.PI / 2 ? 'end' : 'start',
  };
}

export default function SunburstChart({ data }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [tooltip, setTooltip] = useState(null);
  const [currentZoom, setCurrentZoom] = useState(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    const ro = new ResizeObserver(() => {
      setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 300) });
    });
    ro.observe(container);
    setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 300) });
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!data?.tree || !svgRef.current || !window.d3) return;
    setCurrentZoom(null);

    const d3 = window.d3;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = size.w || svgRef.current.clientWidth || 800;
    const height = size.h || svgRef.current.clientHeight || 600;
    const radius = Math.min(width, height) / 2;

    const root = d3.hierarchy(data.tree).sum((d) => Math.max(d.loc || 0, 1));
    d3.partition().size([2 * Math.PI, radius])(root);

    const g = svg
      .append('g')
      .attr('transform', `translate(${width / 2},${height / 2})`);

    const arc = d3
      .arc()
      .startAngle((d) => d.x0)
      .endAngle((d) => d.x1)
      .innerRadius((d) => d.y0)
      .outerRadius((d) => d.y1);

    const descendants = root.descendants().filter((d) => d.depth > 0);

    const paths = g
      .selectAll('path')
      .data(descendants)
      .enter()
      .append('path')
      .attr('d', arc)
      .attr('fill', (d) => COLOR_MAP[d.data.language] || COLOR_DEFAULT)
      .attr('opacity', 0.85)
      .attr('stroke', 'hsl(var(--background))')
      .attr('stroke-width', 1)
      .style('cursor', 'pointer');

    paths
      .on('click', function (event, d) {
        event.stopPropagation();
        const current = currentZoom;
        if (current && current === d) {
          resetZoom();
          return;
        }
        setCurrentZoom(d);
        const kx = (2 * Math.PI) / (d.x1 - d.x0);
        const ky = radius / (d.y1 - d.y0);
        g.transition()
          .duration(750)
          .attr(
            'transform',
            `translate(${width / 2},${height / 2}) scale(${Math.min(kx, ky)}) rotate(${(-d.x0 * 180) / Math.PI})`,
          );
        paths.transition().duration(750).attr('d', (n) =>
          arc(
            Object.assign({}, n, {
              x0: (n.x0 - d.x0) * kx,
              x1: (n.x1 - d.x0) * kx,
              y0: (n.y0 - d.y0) * ky,
              y1: (n.y1 - d.y0) * ky,
            }),
          ),
        );
      })
      .on('mousemove', function(event, d) {
        event.stopPropagation();
        const lang = d.data.language || '?';
        setTooltip({
          x: event.clientX + 12,
          y: event.clientY - 8,
          html: `<strong>${d.data.name}</strong><br/>${lang}<br/>${d.value} LOC`,
        });
      })
      .on('mouseleave', function() {
        setTooltip(null);
      })
      .on('mouseover', function (_event, d) {
        const lang = d.data.language;
        d3.select(this).attr('opacity', 1).attr('stroke-width', 2);
        if (lang) {
          paths.attr('opacity', (n) => (n.data.language === lang ? 1 : 0.35));
        }
      })
      .on('mouseout', function () {
        paths.attr('opacity', 0.85).attr('stroke-width', 1);
        setTooltip(null);
      });

    const labelG = g.append('g').attr('class', 'labels');

    labelG
      .selectAll('text')
      .data(descendants.filter((d) => {
        const arcLen = (d.y1 - d.y0) * ((d.x1 - d.x0) / 2);
        return arcLen > 18 && (d.x1 - d.x0) > 0.12;
      }))
      .join('text')
      .attr('transform', (d) => {
        const c = centroidLabel(d);
        return `translate(${c.x},${c.y}) rotate(${c.rotation})`;
      })
      .attr('text-anchor', (d) => centroidLabel(d).anchor)
      .attr('dy', '0.35em')
      .attr('font-size', (d) => {
        const depthScale = Math.max(7, 11 - d.depth);
        return depthScale + 'px';
      })
      .attr('fill', (d) => textColorForBackground(COLOR_MAP[d.data.language] || COLOR_DEFAULT))
      .style('pointer-events', 'none')
      .style('text-shadow', '0 1px 2px rgba(0,0,0,0.4)')
      .text((d) => {
        const arcLen = (d.y1 - d.y0) * ((d.x1 - d.x0) / 2);
        const maxChars = Math.floor(arcLen / 4.5);
        const name = d.data.name;
        return name.length > maxChars && maxChars > 1 ? name.substring(0, maxChars) + '…' : name;
      });

    function resetZoom() {
      setCurrentZoom(null);
      g.transition()
        .duration(750)
        .attr('transform', `translate(${width / 2},${height / 2})`);
      paths.transition().duration(750).attr('d', arc);
    }

    svg.on('click', () => {
      resetZoom();
    });

  }, [data, size]);

  return React.createElement('div', {
    ref: containerRef,
    style: { width: '100%', height: '100%', minHeight: '300px', position: 'relative' },
    children: [
      React.createElement('svg', {
        key: 'svg',
        ref: svgRef,
        className: 'codebase-viz-sunburst',
        style: { width: '100%', height: '100%', display: 'block' },
      }),
      tooltip && React.createElement('div', {
        key: 'tooltip',
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
    ],
  });
}
