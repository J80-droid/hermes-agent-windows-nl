import React from 'react';

const h = React.createElement;

export default function HistoryChart({ data }) {
  const svgRef = React.useRef(null);
  const points = data?.points || [];

  React.useEffect(() => {
    if (!svgRef.current || !points.length || !window.d3) return undefined;
    const d3 = window.d3;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    const width = svgRef.current.clientWidth || 600;
    const height = 180;
    svg.attr('width', width).attr('height', height);

    const xs = points.map((_, i) => i);
    const ys = points.map((p) => p.loc || 0);
    const x = d3.scaleLinear().domain([0, Math.max(xs.length - 1, 1)]).range([40, width - 10]);
    const y = d3.scaleLinear().domain([0, d3.max(ys) || 1]).nice().range([height - 20, 10]);

    const line = d3
      .line()
      .x((_, i) => x(i))
      .y((_, i) => y(ys[i]));

    svg
      .append('path')
      .datum(points)
      .attr('fill', 'none')
      .attr('stroke', 'hsl(var(--primary))')
      .attr('stroke-width', 2)
      .attr('d', line);

    return undefined;
  }, [points]);

  if (!points.length) {
    return h('p', { className: 'codebase-viz-empty' }, 'Geen history-data.');
  }

  return h('svg', { ref: svgRef, style: { width: '100%', minHeight: '180px' } });
}
