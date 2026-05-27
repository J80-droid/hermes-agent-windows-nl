import React, { useEffect, useRef } from 'react';

const COLOR_MAP = {
  Python: '#3572A5',
  TypeScript: '#3178C6',
  JavaScript: '#F7DF1E',
  HTML: '#E34F26',
  CSS: '#563D7C',
  Shell: '#89E051',
  Markdown: '#083FA1',
  YAML: '#CB171E',
  JSON: '#292929',
  Dockerfile: '#384D54',
};
const COLOR_DEFAULT = '#6B7280';

export default function SunburstChart({ data }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!data?.tree || !svgRef.current || !window.d3) return;

    const d3 = window.d3;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 800;
    const height = svgRef.current.clientHeight || 600;
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

    const paths = g
      .selectAll('path')
      .data(root.descendants().filter((d) => d.depth > 0))
      .enter()
      .append('path')
      .attr('d', arc)
      .attr('fill', (d) => COLOR_MAP[d.data.language] || COLOR_DEFAULT)
      .attr('opacity', 0.6)
      .attr('stroke', 'hsl(var(--background))')
      .attr('stroke-width', 1);

    let currentZoom = null;

    paths.on('click', function (event, d) {
      event.stopPropagation();
      if (currentZoom === d) {
        currentZoom = null;
        g.transition()
          .duration(750)
          .attr('transform', `translate(${width / 2},${height / 2})`);
        paths.transition().duration(750).attr('d', arc);
        return;
      }
      currentZoom = d;
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
    });

    paths
      .on('mouseover', function (_event, d) {
        const lang = d.data.language;
        d3.select(this).attr('opacity', 0.9).attr('stroke-width', 2);
        if (lang) {
          paths.attr('opacity', (n) => (n.data.language === lang ? 1 : 0.25));
        }
      })
      .on('mouseout', function () {
        paths.attr('opacity', 0.6).attr('stroke-width', 1);
      });

    svg.on('click', () => {
      currentZoom = null;
      g.transition()
        .duration(750)
        .attr('transform', `translate(${width / 2},${height / 2})`);
      paths.transition().duration(750).attr('d', arc);
    });
  }, [data]);

  return React.createElement('svg', {
    ref: svgRef,
    className: 'codebase-viz-sunburst',
    style: { width: '100%', height: '100%', minHeight: '480px' },
  });
}
