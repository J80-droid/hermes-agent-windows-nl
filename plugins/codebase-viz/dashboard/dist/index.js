var CodebaseVizPlugin = (() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __require = /* @__PURE__ */ ((x) => typeof require !== "undefined" ? require : typeof Proxy !== "undefined" ? new Proxy(x, {
    get: (a, b) => (typeof require !== "undefined" ? require : a)[b]
  }) : x)(function(x) {
    if (typeof require !== "undefined") return require.apply(this, arguments);
    throw Error('Dynamic require of "' + x + '" is not supported');
  });
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // src/App.jsx
  var import_react12 = __toESM(__require("react"));

  // src/SunburstChart.jsx
  var import_react = __toESM(__require("react"));
  var COLOR_MAP = {
    Python: "#3572A5",
    TypeScript: "#3178C6",
    JavaScript: "#F7DF1E",
    HTML: "#E34F26",
    CSS: "#563D7C",
    Shell: "#89E051",
    Markdown: "#083FA1",
    YAML: "#CB171E",
    JSON: "#292929",
    Dockerfile: "#384D54"
  };
  var COLOR_DEFAULT = "#6B7280";
  function SunburstChart({ data }) {
    const svgRef = (0, import_react.useRef)(null);
    (0, import_react.useEffect)(() => {
      if (!data?.tree || !svgRef.current || !window.d3) return;
      const d3 = window.d3;
      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      const width = svgRef.current.clientWidth || 800;
      const height = svgRef.current.clientHeight || 600;
      const radius = Math.min(width, height) / 2;
      const root = d3.hierarchy(data.tree).sum((d) => Math.max(d.loc || 0, 1));
      d3.partition().size([2 * Math.PI, radius])(root);
      const g = svg.append("g").attr("transform", `translate(${width / 2},${height / 2})`);
      const arc = d3.arc().startAngle((d) => d.x0).endAngle((d) => d.x1).innerRadius((d) => d.y0).outerRadius((d) => d.y1);
      const paths = g.selectAll("path").data(root.descendants().filter((d) => d.depth > 0)).enter().append("path").attr("d", arc).attr("fill", (d) => COLOR_MAP[d.data.language] || COLOR_DEFAULT).attr("opacity", 0.6).attr("stroke", "hsl(var(--background))").attr("stroke-width", 1);
      let currentZoom = null;
      paths.on("click", function(event, d) {
        event.stopPropagation();
        if (currentZoom === d) {
          currentZoom = null;
          g.transition().duration(750).attr("transform", `translate(${width / 2},${height / 2})`);
          paths.transition().duration(750).attr("d", arc);
          return;
        }
        currentZoom = d;
        const kx = 2 * Math.PI / (d.x1 - d.x0);
        const ky = radius / (d.y1 - d.y0);
        g.transition().duration(750).attr(
          "transform",
          `translate(${width / 2},${height / 2}) scale(${Math.min(kx, ky)}) rotate(${-d.x0 * 180 / Math.PI})`
        );
        paths.transition().duration(750).attr(
          "d",
          (n) => arc(
            Object.assign({}, n, {
              x0: (n.x0 - d.x0) * kx,
              x1: (n.x1 - d.x0) * kx,
              y0: (n.y0 - d.y0) * ky,
              y1: (n.y1 - d.y0) * ky
            })
          )
        );
      });
      paths.on("mouseover", function(_event, d) {
        const lang = d.data.language;
        d3.select(this).attr("opacity", 0.9).attr("stroke-width", 2);
        if (lang) {
          paths.attr("opacity", (n) => n.data.language === lang ? 1 : 0.25);
        }
      }).on("mouseout", function() {
        paths.attr("opacity", 0.6).attr("stroke-width", 1);
      });
      svg.on("click", () => {
        currentZoom = null;
        g.transition().duration(750).attr("transform", `translate(${width / 2},${height / 2})`);
        paths.transition().duration(750).attr("d", arc);
      });
    }, [data]);
    return import_react.default.createElement("svg", {
      ref: svgRef,
      className: "codebase-viz-sunburst",
      style: { width: "100%", height: "100%", minHeight: "480px" }
    });
  }

  // src/MetricsTab.jsx
  var import_react4 = __toESM(__require("react"));

  // src/usePluginFetch.js
  var import_react2 = __toESM(__require("react"));
  var API = "/api/plugins/codebase-viz";
  function usePluginFetch(path, deps = []) {
    const SDK = window.__HERMES_PLUGIN_SDK__;
    const [data, setData] = import_react2.default.useState(null);
    const [error, setError] = import_react2.default.useState(null);
    const [loading, setLoading] = import_react2.default.useState(true);
    import_react2.default.useEffect(() => {
      if (!SDK?.fetchJSON || !path) return void 0;
      const ac = new AbortController();
      setLoading(true);
      setError(null);
      SDK.fetchJSON(`${API}${path}`, { signal: ac.signal }).then((body) => {
        if (!ac.signal.aborted) setData(body);
      }).catch((err) => {
        if (err?.name !== "AbortError" && !ac.signal.aborted) setError(err);
      }).finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
      return () => ac.abort();
    }, [path, ...deps]);
    return { data, error, loading };
  }
  async function postForceScan() {
    const SDK = window.__HERMES_PLUGIN_SDK__;
    if (!SDK?.fetchJSON) return;
    await SDK.fetchJSON(`${API}/force-scan`, { method: "POST" });
  }
  function useD3Loader() {
    const [ready, setReady] = import_react2.default.useState(!!window.d3);
    import_react2.default.useEffect(() => {
      if (window.d3) {
        setReady(true);
        return void 0;
      }
      const src = "/dashboard-plugins/codebase-viz/dist/d3.v7.min.js";
      const existing = document.querySelector(`script[data-codebase-viz-d3="1"]`);
      if (existing) {
        existing.addEventListener("load", () => setReady(true));
        return void 0;
      }
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.dataset.codebaseVizD3 = "1";
      s.onload = () => setReady(true);
      s.onerror = () => setReady(false);
      document.head.appendChild(s);
      return () => {
      };
    }, []);
    return ready;
  }

  // src/HistoryChart.jsx
  var import_react3 = __toESM(__require("react"));
  var h = import_react3.default.createElement;
  function HistoryChart({ data }) {
    const svgRef = import_react3.default.useRef(null);
    const points = data?.points || [];
    import_react3.default.useEffect(() => {
      if (!svgRef.current || !points.length || !window.d3) return void 0;
      const d3 = window.d3;
      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      const width = svgRef.current.clientWidth || 600;
      const height = 180;
      svg.attr("width", width).attr("height", height);
      const xs = points.map((_, i) => i);
      const ys = points.map((p) => p.loc || 0);
      const x = d3.scaleLinear().domain([0, Math.max(xs.length - 1, 1)]).range([40, width - 10]);
      const y = d3.scaleLinear().domain([0, d3.max(ys) || 1]).nice().range([height - 20, 10]);
      const line = d3.line().x((_, i) => x(i)).y((_, i) => y(ys[i]));
      svg.append("path").datum(points).attr("fill", "none").attr("stroke", "hsl(var(--primary))").attr("stroke-width", 2).attr("d", line);
      return void 0;
    }, [points]);
    if (!points.length) {
      return h("p", { className: "codebase-viz-empty" }, "Geen history-data.");
    }
    return h("svg", { ref: svgRef, style: { width: "100%", minHeight: "180px" } });
  }

  // src/MetricsTab.jsx
  var h2 = import_react4.default.createElement;
  function ratioClass(ratio) {
    if (ratio >= 1 && ratio <= 3) return "status-ok";
    if (ratio > 3) return "status-warn";
    return "status-err";
  }
  function MetricsTab({ data }) {
    if (!data) return null;
    const { data: history } = usePluginFetch("/history", []);
    const { Card, CardHeader, CardTitle, CardContent } = window.__HERMES_PLUGIN_SDK__.components;
    const langs = Object.entries(data.languages || {}).sort(
      (a, b) => (b[1].code || 0) - (a[1].code || 0)
    );
    return h2(
      "div",
      { className: "codebase-viz-metrics" },
      h2(
        "div",
        { className: "codebase-viz-metrics-grid" },
        h2(MetricCard, { label: "Total LOC", value: data.total_loc }),
        h2(MetricCard, { label: "Files", value: data.total_files }),
        h2(MetricCard, { label: "Languages", value: data.language_count }),
        h2(MetricCard, {
          label: "Prod : Test",
          value: `${data.ratio}:1`,
          valueClass: ratioClass(data.ratio)
        })
      ),
      h2(
        Card,
        null,
        h2(CardHeader, null, h2(CardTitle, null, "Languages")),
        h2(
          CardContent,
          null,
          h2(
            "table",
            { className: "codebase-viz-table" },
            h2(
              "thead",
              null,
              h2("tr", null, h2("th", null, "Language"), h2("th", null, "Files"), h2("th", null, "LOC"))
            ),
            h2(
              "tbody",
              null,
              ...langs.map(
                ([name, stats]) => h2(
                  "tr",
                  { key: name },
                  h2("td", null, name),
                  h2("td", null, stats.files),
                  h2("td", null, stats.code)
                )
              )
            )
          )
        )
      ),
      history?.points?.length ? h2(
        Card,
        null,
        h2(CardHeader, null, h2(CardTitle, null, "LOC trend (commits)")),
        h2(CardContent, null, h2(HistoryChart, { data: history }))
      ) : null,
      data.top_files?.length ? h2(
        Card,
        null,
        h2(CardHeader, null, h2(CardTitle, null, "Top files by LOC")),
        h2(
          CardContent,
          null,
          h2(
            "ul",
            { className: "codebase-viz-list" },
            ...data.top_files.map(
              (f) => h2("li", { key: f.path }, `${f.name} \u2014 ${f.loc} (${f.language || "?"})`)
            )
          )
        )
      ) : null
    );
  }
  function MetricCard({ label, value, valueClass }) {
    const { Card, CardContent } = window.__HERMES_PLUGIN_SDK__.components;
    return h2(
      Card,
      null,
      h2(
        CardContent,
        { className: "codebase-viz-metric-card" },
        h2("div", { className: "codebase-viz-metric-label" }, label),
        h2("div", { className: `codebase-viz-metric-value ${valueClass || ""}` }, value)
      )
    );
  }

  // src/HealthTab.jsx
  var import_react5 = __toESM(__require("react"));
  var h3 = import_react5.default.createElement;
  function StatusBadge({ status }) {
    if (status === "error") return h3("span", { className: "status-err" }, "Error");
    if (status === "warning") return h3("span", { className: "status-warn" }, "Warning");
    return h3("span", { className: "status-ok" }, "OK");
  }
  function HealthSection({ section }) {
    const errors = section.checks.filter((c) => c.status === "error");
    const warnings = section.checks.filter((c) => c.status === "warning");
    return h3(
      "div",
      { className: "codebase-viz-health-section" },
      h3("div", { className: "codebase-viz-health-section-title" }, section.name),
      ...errors.map(
        (c) => h3(
          "div",
          { key: c.text, className: "codebase-viz-health-line" },
          h3(StatusBadge, { status: "error" }),
          " ",
          c.text
        )
      ),
      ...warnings.map(
        (c) => h3(
          "div",
          { key: c.text, className: "codebase-viz-health-line" },
          h3(StatusBadge, { status: "warning" }),
          " ",
          c.text
        )
      )
    );
  }
  function HealthTab({ data }) {
    if (!data?.sections) {
      return h3("p", null, data?.error || "Geen doctor-data.");
    }
    const { Button } = window.__HERMES_PLUGIN_SDK__.components;
    const { summary } = data;
    const score = summary?.score || 0;
    const overallClass = score >= 90 ? "status-ok" : score >= 70 ? "status-warn" : "status-err";
    return h3(
      "div",
      { className: "codebase-viz-health" },
      h3(
        "div",
        { className: "codebase-viz-health-header" },
        h3("span", { className: overallClass }, `Health: ${summary.overall}`),
        ` (${score}%) \u2014 `,
        h3("span", { className: "status-ok" }, `${summary.ok} OK`),
        " ",
        h3("span", { className: "status-warn" }, `${summary.warnings} warnings`),
        " ",
        h3("span", { className: "status-err" }, `${summary.errors} errors`),
        h3(
          Button,
          {
            variant: "outline",
            size: "sm",
            style: { marginLeft: "1rem" },
            onClick: () => postForceScan().then(() => window.location.reload())
          },
          "Refresh"
        )
      ),
      h3(
        "div",
        { className: "codebase-viz-health-grid" },
        ...data.sections.map(
          (section) => h3(HealthSection, { key: section.name, section })
        )
      ),
      h3(
        "details",
        { style: { marginTop: "1rem" } },
        h3("summary", null, "Raw doctor output"),
        h3("pre", { className: "codebase-viz-raw" }, data.raw)
      )
    );
  }

  // src/ForceGraph.jsx
  var import_react7 = __toESM(__require("react"));

  // src/useFileWatcher.js
  var import_react6 = __toESM(__require("react"));

  // src/wsAuth.js
  function getSessionToken() {
    if (typeof window !== "undefined" && window.__HERMES_SESSION_TOKEN__) {
      return String(window.__HERMES_SESSION_TOKEN__);
    }
    try {
      const cookie = document.cookie.split("; ").find((r) => r.startsWith("hermes_session_token="));
      if (cookie) {
        return decodeURIComponent(cookie.split("=").slice(1).join("="));
      }
    } catch (_e) {
    }
    return "";
  }

  // src/useFileWatcher.js
  var h4 = import_react6.default.createElement;
  function useFileWatcher(opts = {}) {
    const { onEvent, reconnectDelay = 3e3 } = opts;
    const [connected, setConnected] = import_react6.default.useState(false);
    const [lastEvent, setLastEvent] = import_react6.default.useState(null);
    const [reconnect, setReconnect] = import_react6.default.useState(0);
    import_react6.default.useEffect(() => {
      const token = getSessionToken();
      if (!token) return void 0;
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${proto}//${window.location.host}/api/plugins/codebase-viz/events?token=${encodeURIComponent(token)}`;
      let ws;
      let reconnectTimer;
      let destroyed = false;
      function connect() {
        if (destroyed) return;
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
          if (!destroyed) setConnected(true);
        };
        ws.onclose = () => {
          if (destroyed) return;
          setConnected(false);
          reconnectTimer = setTimeout(() => {
            setReconnect((n) => n + 1);
            connect();
          }, reconnectDelay);
        };
        ws.onmessage = (evt) => {
          if (destroyed) return;
          try {
            const msg = JSON.parse(evt.data);
            if (msg.type === "changes" && Array.isArray(msg.events)) {
              msg.events.forEach((event) => {
                setLastEvent(event);
                if (typeof onEvent === "function") onEvent(event);
              });
            } else if (msg.type === "connected") {
              setConnected(true);
            } else if (msg.type === "ping") {
              if (ws?.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "pong" }));
              }
            }
          } catch (_e) {
          }
        };
        ws.onerror = () => {
        };
      }
      connect();
      return () => {
        destroyed = true;
        clearTimeout(reconnectTimer);
        if (ws) {
          ws.onclose = null;
          ws.close();
        }
      };
    }, [reconnectDelay]);
    return { connected, lastEvent, reconnect };
  }
  function FileWatcherIndicator({ connected }) {
    return h4(
      "span",
      {
        className: connected ? "status-ok" : "status-err",
        style: { fontSize: "0.75rem", whiteSpace: "nowrap" }
      },
      connected ? "Live" : "Offline"
    );
  }
  function useRippleAnimation(lastEvent) {
    const [ripple, setRipple] = import_react6.default.useState(null);
    import_react6.default.useEffect(() => {
      if (!lastEvent) return void 0;
      if (lastEvent.is_directory || lastEvent.type !== "modified" && lastEvent.type !== "created") {
        return void 0;
      }
      setRipple({ path: lastEvent.path, time: Date.now() });
      const timer = setTimeout(() => setRipple(null), 2e3);
      return () => clearTimeout(timer);
    }, [lastEvent]);
    return ripple;
  }

  // src/ForceGraph.jsx
  var h5 = import_react7.default.createElement;
  var MAX_NODES = 500;
  function pathToModuleId(filePath, nodeIds) {
    if (!filePath || !nodeIds?.length) return null;
    const norm = String(filePath).replace(/\\/g, "/");
    const base = norm.split("/").pop() || "";
    const stem = base.replace(/\.py$/i, "").replace(/\.__init__$/, "");
    const candidates = /* @__PURE__ */ new Set([stem, stem.replace(/\//g, ".")]);
    for (const id of nodeIds) {
      if (candidates.has(id) || id.endsWith(`.${stem}`) || id.split(".").pop() === stem) {
        return id;
      }
    }
    return null;
  }
  function buildGraph(data, search) {
    const allEdges = Array.isArray(data?.edges) ? data.edges : [];
    const edges = search ? allEdges.filter(
      (e) => e.source.toLowerCase().includes(search.toLowerCase()) || e.target.toLowerCase().includes(search.toLowerCase())
    ) : allEdges;
    const nodeSet = /* @__PURE__ */ new Set();
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
      nodes = nodes.sort((a, b) => (degree[b.id] || 0) - (degree[a.id] || 0)).slice(0, MAX_NODES);
      const allowed = new Set(nodes.map((n) => n.id));
      return {
        nodes,
        links: edges.filter((e) => allowed.has(e.source) && allowed.has(e.target)).map((e) => ({ source: e.source, target: e.target, type: e.type })),
        capped: true
      };
    }
    return {
      nodes,
      links: edges.map((e) => ({
        source: e.source,
        target: e.target,
        type: e.type
      })),
      capped: false
    };
  }
  function ForceGraph({ data }) {
    const svgRef = import_react7.default.useRef(null);
    const containerRef = import_react7.default.useRef(null);
    const simRef = import_react7.default.useRef(null);
    const [search, setSearch] = import_react7.default.useState("");
    const [inspector, setInspector] = import_react7.default.useState(null);
    const [size, setSize] = import_react7.default.useState({ w: 0, h: 0 });
    const { connected, lastEvent } = useFileWatcher();
    const ripple = useRippleAnimation(lastEvent);
    import_react7.default.useEffect(() => {
      const container = containerRef.current;
      if (!container) return void 0;
      const ro = new ResizeObserver(() => {
        setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 400) });
      });
      ro.observe(container);
      setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 400) });
      return () => ro.disconnect();
    }, []);
    import_react7.default.useEffect(() => {
      const svg = svgRef.current;
      if (!svg || !data?.nodes?.length || size.w < 10) return void 0;
      const d3 = window.d3;
      if (!d3) return void 0;
      const { nodes, links, capped: capped2 } = buildGraph(data, search);
      if (!nodes.length) return void 0;
      const width = size.w;
      const height = size.h;
      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.innerHTML = "";
      const g = d3.select(svg).append("g");
      const zoom = d3.zoom().scaleExtent([0.1, 4]).on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
      d3.select(svg).call(zoom);
      const simulation = d3.forceSimulation(nodes).force("link", d3.forceLink(links).id((d) => d.id).distance(80)).force("charge", d3.forceManyBody().strength(-200)).force("center", d3.forceCenter(width / 2, height / 2)).force("collision", d3.forceCollide().radius(20));
      simRef.current = simulation;
      const link = g.append("g").selectAll("line").data(links).join("line").attr("stroke", "hsl(var(--muted-foreground) / 0.3)").attr("stroke-width", 1).attr("stroke-dasharray", (d) => d.type === "from_import" ? "3,2" : "0");
      const node = g.append("g").selectAll("circle").data(nodes).join("circle").attr("r", 6).attr("fill", "hsl(var(--primary))").attr("stroke", "hsl(var(--border))").attr("stroke-width", 1).style("cursor", "pointer").call(
        d3.drag().on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        }).on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        }).on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      ).on("click", (_event, d) => setInspector(d.id));
      const label = g.append("g").selectAll("text").data(nodes).join("text").text((d) => d.id.split(".").pop()).attr("font-size", "10px").attr("dx", 8).attr("dy", 3).attr("fill", "hsl(var(--foreground) / 0.8)");
      function drawRipplePulse() {
        if (!ripple?.path) return;
        const targetId = pathToModuleId(
          ripple.path,
          nodes.map((n) => n.id)
        );
        const target = targetId ? nodes.find((n) => n.id === targetId) : null;
        const cx = target?.x ?? width / 2;
        const cy = target?.y ?? height / 2;
        g.append("circle").attr("cx", cx).attr("cy", cy).attr("r", 6).attr("fill", "none").attr("stroke", "#22c55e").attr("stroke-width", 2).transition().duration(1e3).attr("r", 40).attr("stroke-width", 0).remove();
      }
      if (ripple?.path) {
        simulation.on("end", drawRipplePulse);
      }
      simulation.on("tick", () => {
        link.attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y).attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
        node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
        label.attr("x", (d) => d.x).attr("y", (d) => d.y);
      });
      return () => {
        simulation.stop();
        simRef.current = null;
      };
    }, [data, search, ripple, size]);
    const edgeList = Array.isArray(data?.edges) ? data.edges : [];
    const inEdges = inspector ? edgeList.filter((e) => e.target === inspector).slice(0, 20) : [];
    const outEdges = inspector ? edgeList.filter((e) => e.source === inspector).slice(0, 20) : [];
    return h5(
      "div",
      { style: { display: "flex", flexDirection: "column", height: "100%" } },
      h5(
        "div",
        {
          style: {
            display: "flex",
            gap: "0.5rem",
            alignItems: "center",
            padding: "0.5rem 0",
            flexShrink: 0
          }
        },
        h5("input", {
          type: "text",
          placeholder: "Zoek module...",
          value: search,
          onChange: (e) => setSearch(e.target.value),
          style: {
            flex: 1,
            padding: "0.3rem 0.5rem",
            fontSize: "0.8rem",
            background: "hsl(var(--input))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "0.25rem",
            color: "hsl(var(--foreground))"
          }
        }),
        h5(FileWatcherIndicator, { connected })
      ),
      capped && h5(
        "p",
        { className: "codebase-viz-hint", style: { margin: "0 0 0.25rem" } },
        `Grafiek beperkt tot ${MAX_NODES} modules (meest verbonden eerst).`
      ),
      inspector && h5(
        "div",
        {
          className: "codebase-viz-inspector",
          style: {
            padding: "0.5rem",
            background: "hsl(var(--accent) / 0.2)",
            borderRadius: "0.25rem",
            fontSize: "0.8rem",
            marginBottom: "0.25rem",
            flexShrink: 0
          }
        },
        h5(
          "div",
          { style: { display: "flex", justifyContent: "space-between", marginBottom: "0.35rem" } },
          h5("strong", null, inspector),
          h5(
            "button",
            {
              type: "button",
              onClick: () => setInspector(null),
              style: {
                background: "transparent",
                border: "1px solid hsl(var(--border))",
                borderRadius: "0.25rem",
                cursor: "pointer",
                fontSize: "0.75rem",
                padding: "0.15rem 0.4rem"
              }
            },
            "Sluiten"
          )
        ),
        h5("div", null, h5("span", { className: "status-ok" }, "Uit "), `${outEdges.length} imports`),
        outEdges.length > 0 && h5(
          "ul",
          { style: { margin: "0.2rem 0 0.4rem", paddingLeft: "1.2rem" } },
          outEdges.map((e) => h5("li", { key: e.target + e.type }, e.target))
        ),
        h5("div", null, h5("span", { className: "status-err" }, "In "), `${inEdges.length} imports`),
        inEdges.length > 0 && h5(
          "ul",
          { style: { margin: "0.2rem 0", paddingLeft: "1.2rem" } },
          inEdges.map((e) => h5("li", { key: e.source + e.type }, e.source))
        )
      ),
      h5("div", {
        ref: containerRef,
        style: { flex: 1, minHeight: 0, overflow: "hidden" },
        children: h5("svg", { ref: svgRef, style: { width: "100%", height: "100%" } })
      })
    );
  }

  // src/TreemapChart.jsx
  var import_react8 = __toESM(__require("react"));
  var h6 = import_react8.default.createElement;
  var LANG_COLORS = {
    python: "#3776AB",
    javascript: "#F7DF1E",
    typescript: "#3178C6",
    jsx: "#61DAFB",
    tsx: "#3178C6",
    markdown: "#083FA1",
    json: "#292929",
    yaml: "#6CB2E6",
    html: "#E34F26",
    css: "#1572B6",
    shell: "#4EAA25",
    powershell: "#012456",
    sql: "#E38C00",
    dockerfile: "#2496ED",
    makefile: "#427819",
    rust: "#DEA584",
    go: "#00ADD8",
    "c#": "#178600",
    ruby: "#CC342D",
    php: "#777BB4",
    java: "#ED8B00",
    kotlin: "#7F52FF",
    scala: "#DC322F",
    swift: "#F05138"
  };
  function subtreeLoc(node) {
    if (!node) return 0;
    if (node.type === "file") return node.loc || 0;
    return (node.children || []).reduce((sum, ch) => sum + subtreeLoc(ch), 0);
  }
  function getColor(lang, d3) {
    if (!lang) return "hsl(var(--primary))";
    const base = LANG_COLORS[lang.toLowerCase()];
    if (base) return base;
    if (!d3) return "hsl(var(--primary))";
    const hue = lang.split("").reduce((a, c) => a + c.charCodeAt(0), 0) * 13.7 % 360;
    return d3.hsl(hue, 0.5, 0.5).formatHex();
  }
  function immediateChildren(treeNode) {
    return (treeNode.children || []).map((c) => ({
      name: c.name,
      type: c.type,
      language: c.language,
      loc: c.type === "file" ? c.loc || 0 : subtreeLoc(c),
      children: c.children,
      _raw: c
    })).filter((c) => c.loc > 0);
  }
  function TreemapChart({ data }) {
    const svgRef = import_react8.default.useRef(null);
    const containerRef = import_react8.default.useRef(null);
    const [zoomStack, setZoomStack] = import_react8.default.useState([]);
    const treeData = data?.tree || { name: "root", children: [], loc: 0 };
    const currentData = zoomStack.length > 0 ? zoomStack[zoomStack.length - 1] : treeData;
    function zoomTo(node) {
      setZoomStack((prev) => [...prev, node]);
    }
    function zoomOut() {
      setZoomStack((prev) => prev.length > 1 ? prev.slice(0, -1) : []);
    }
    import_react8.default.useEffect(() => {
      const container = containerRef.current;
      const svg = svgRef.current;
      if (!container || !svg) return void 0;
      const d3 = window.d3;
      if (!d3) return void 0;
      const width = container.clientWidth;
      const height = Math.max(container.clientHeight, 400);
      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      svg.innerHTML = "";
      const items = immediateChildren(currentData);
      if (!items.length) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", String(width / 2));
        label.setAttribute("y", String(height / 2));
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("fill", "hsl(var(--muted-foreground))");
        label.setAttribute("font-size", "14");
        label.textContent = "Geen data voor deze directory";
        svg.appendChild(label);
        return void 0;
      }
      const root = d3.hierarchy({ name: "root", children: items }).sum((d) => d.loc || 0).sort((a, b) => (b.value || 0) - (a.value || 0));
      d3.treemap().size([width, height]).paddingOuter(2).paddingInner(1).round(true)(root);
      const cells = root.children || [];
      if (!cells.length) return void 0;
      const g = d3.select(svg).append("g");
      g.selectAll("rect").data(cells).join("rect").attr("x", (d) => d.x0).attr("y", (d) => d.y0).attr("width", (d) => Math.max(0, d.x1 - d.x0)).attr("height", (d) => Math.max(0, d.y1 - d.y0)).attr(
        "fill",
        (d) => d.data.type === "dir" ? "hsl(var(--muted-foreground) / 0.25)" : getColor(d.data.language, d3)
      ).attr("stroke", "hsl(var(--background))").attr("stroke-width", 1).style(
        "cursor",
        (d) => d.data.type === "dir" && d.data._raw?.children?.length ? "pointer" : "default"
      ).on("click", (_event, d) => {
        if (d.data.type === "dir" && d.data._raw?.children?.length) {
          zoomTo(d.data._raw);
        }
      }).append("title").text((d) => {
        const kind = d.data.type === "dir" ? "map" : d.data.language || "?";
        return `${d.data.name}
${kind}
${d.value} LOC`;
      });
      g.selectAll("text.label").data(cells).join("text").attr("class", "label").attr("x", (d) => d.x0 + 3).attr("y", (d) => d.y0 + 12).attr("font-size", "10px").attr("fill", (d) => d.data.type === "dir" ? "hsl(var(--foreground))" : "#fff").style("pointer-events", "none").style(
        "text-shadow",
        (d) => d.data.type === "dir" ? "none" : "0 1px 2px rgba(0,0,0,0.6)"
      ).text((d) => {
        const w = d.x1 - d.x0;
        if (w < 40) return "";
        const label = d.data.type === "dir" ? `${d.data.name}/` : d.data.name;
        return label.length * 7 > w ? `${label.substring(0, Math.floor(w / 7))}\u2026` : label;
      }).style("opacity", (d) => {
        const area = (d.x1 - d.x0) * (d.y1 - d.y0);
        return area < 600 ? 0 : 1;
      });
      return void 0;
    }, [currentData]);
    const crumbs = zoomStack.length ? zoomStack : [treeData];
    return h6(
      "div",
      { style: { display: "flex", flexDirection: "column", height: "100%" } },
      h6(
        "div",
        {
          style: {
            display: "flex",
            gap: "0.25rem",
            alignItems: "center",
            padding: "0.5rem 0",
            flexShrink: 0,
            fontSize: "0.8rem",
            flexWrap: "wrap"
          }
        },
        h6(
          "button",
          {
            type: "button",
            onClick: zoomOut,
            disabled: !zoomStack.length,
            style: {
              background: "transparent",
              border: "1px solid hsl(var(--border))",
              borderRadius: "0.25rem",
              cursor: zoomStack.length ? "pointer" : "default",
              fontSize: "0.75rem",
              padding: "0.15rem 0.4rem",
              opacity: zoomStack.length ? 1 : 0.4
            }
          },
          "\u2190 Terug"
        ),
        crumbs.map(
          (node, i) => h6(
            "span",
            { key: `${node.path || node.name}-${i}`, style: { color: "hsl(var(--muted-foreground))" } },
            i === 0 ? "" : " \u203A ",
            node.name || "root"
          )
        )
      ),
      h6("div", {
        ref: containerRef,
        style: { flex: 1, minHeight: 0, overflow: "hidden" },
        children: h6("svg", { ref: svgRef, style: { width: "100%", height: "100%" } })
      })
    );
  }

  // src/DataTableTab.jsx
  var import_react9 = __toESM(__require("react"));
  var h7 = import_react9.default.createElement;
  function DataTableTab({ data, columns, title, hint }) {
    const { Card, CardHeader, CardTitle, CardContent } = window.__HERMES_PLUGIN_SDK__.components;
    const items = data?.items || data?.frames || data?.points || [];
    const err = data?.error;
    if (err && !items.length) {
      return h7("div", { className: "codebase-viz-empty" }, h7("p", null, err));
    }
    if (!items.length) {
      return h7("div", { className: "codebase-viz-empty" }, h7("p", null, "Geen resultaten."));
    }
    return h7(
      "div",
      { className: "codebase-viz-table-tab" },
      hint && h7("p", { className: "codebase-viz-hint" }, hint),
      data?.coverage_pct != null && h7("p", null, `Geschatte dekking: ${data.coverage_pct}% (${data.covered}/${data.total})`),
      data?.total != null && h7("p", { className: "codebase-viz-hint" }, `Totaal: ${data.total}`),
      h7(
        Card,
        null,
        h7(CardHeader, null, h7(CardTitle, null, title || "Resultaten")),
        h7(
          CardContent,
          null,
          h7(
            "div",
            { className: "codebase-viz-virtual-scroll" },
            h7(
              "table",
              { className: "codebase-viz-table" },
              h7(
                "thead",
                null,
                h7("tr", null, ...columns.map((c) => h7("th", { key: c.key }, c.label)))
              ),
              h7(
                "tbody",
                null,
                ...items.map(
                  (row, i) => h7(
                    "tr",
                    { key: row.file || row.module || row.author || row.sha || i },
                    ...columns.map(
                      (c) => h7("td", { key: c.key }, c.render ? c.render(row) : String(row[c.key] ?? ""))
                    )
                  )
                )
              )
            )
          )
        )
      )
    );
  }

  // src/SearchTab.jsx
  var import_react10 = __toESM(__require("react"));
  var h8 = import_react10.default.createElement;
  function SearchTab() {
    const [query, setQuery] = import_react10.default.useState("");
    const path = query.length >= 2 ? `/search?q=${encodeURIComponent(query)}` : null;
    const { data, error, loading } = usePluginFetch(path, [query]);
    return h8(
      "div",
      null,
      h8("input", {
        type: "search",
        placeholder: "Zoek in codebase (min. 2 tekens)...",
        value: query,
        onChange: (e) => setQuery(e.target.value),
        style: {
          width: "100%",
          padding: "0.5rem",
          marginBottom: "0.75rem",
          fontSize: "0.85rem",
          borderRadius: "0.25rem",
          border: "1px solid hsl(var(--border))",
          background: "hsl(var(--input))",
          color: "hsl(var(--foreground))"
        }
      }),
      query.length < 2 && h8("p", { className: "codebase-viz-hint" }, "Typ minimaal 2 tekens."),
      loading && query.length >= 2 && h8("p", { className: "codebase-viz-loading" }, "Zoeken..."),
      error && h8("p", { className: "codebase-viz-error" }, error.message || "Zoekfout"),
      data && h8(DataTableTab, {
        data,
        title: `Zoekresultaten voor "${query}"`,
        columns: [
          { key: "file", label: "Bestand" },
          { key: "line", label: "Regel" },
          { key: "text", label: "Context" }
        ]
      })
    );
  }

  // src/TimelineTab.jsx
  var import_react11 = __toESM(__require("react"));
  var h9 = import_react11.default.createElement;
  function TimelineTab({ data }) {
    const frames = data?.frames || [];
    if (!frames.length) {
      return h9("p", { className: "codebase-viz-empty" }, "Geen commit-geschiedenis.");
    }
    return h9(
      "div",
      { className: "codebase-viz-timeline" },
      h9("p", { className: "codebase-viz-hint" }, `${frames.length} commits (oud \u2192 nieuw)`),
      h9(
        "ol",
        { style: { fontSize: "0.8rem", maxHeight: "70vh", overflow: "auto", paddingLeft: "1.2rem" } },
        ...frames.map(
          (f) => h9(
            "li",
            { key: f.sha + f.date, style: { marginBottom: "0.35rem" } },
            h9("code", null, f.sha),
            " \u2014 ",
            f.date,
            " \u2014 ",
            f.message
          )
        )
      )
    );
  }

  // src/App.jsx
  var h10 = import_react12.default.createElement;
  var CATEGORIES = [
    {
      id: "visuals",
      label: "Visuals",
      tabs: [
        { id: "sunburst", label: "Sunburst" },
        { id: "force-graph", label: "Force Graph" },
        { id: "treemap", label: "Treemap" },
        { id: "metrics", label: "Metrics" }
      ]
    },
    {
      id: "analysis",
      label: "Analysis",
      tabs: [
        { id: "churn", label: "Churn" },
        { id: "age-map", label: "Age Map" },
        { id: "complexity", label: "Complexity" },
        { id: "todos", label: "TODO/FIXME" },
        { id: "blame", label: "Blame" },
        { id: "coverage", label: "Coverage" },
        { id: "dead-imports", label: "Dead Imports" }
      ]
    },
    {
      id: "hermes",
      label: "Hermes",
      tabs: [
        { id: "health", label: "Health" },
        { id: "config-drift", label: "Config Drift" },
        { id: "session-stats", label: "Session Stats" }
      ]
    },
    {
      id: "tools",
      label: "Tools",
      tabs: [
        { id: "search", label: "Search" },
        { id: "timeline", label: "Timeline" }
      ]
    }
  ];
  var TAB_MAP = {
    sunburst: "/structure",
    "force-graph": "/dependencies",
    treemap: "/structure",
    metrics: "/summary",
    churn: "/churn",
    "age-map": "/age-map",
    complexity: "/complexity",
    todos: "/todos",
    blame: "/blame",
    coverage: "/coverage",
    "dead-imports": "/dead-imports",
    health: "/doctor",
    "config-drift": "/config-drift",
    "session-stats": "/session-stats",
    timeline: "/timeline"
  };
  var TABLE_TABS = {
    churn: {
      title: "Churn (laatste jaar)",
      columns: [
        { key: "file", label: "Bestand" },
        { key: "commits", label: "Commits" }
      ]
    },
    "age-map": {
      title: "Age map",
      columns: [
        { key: "file", label: "Bestand" },
        { key: "last_modified", label: "Laatst gewijzigd" },
        { key: "loc", label: "LOC" }
      ]
    },
    complexity: {
      title: "Complexity (radon)",
      columns: [
        { key: "file", label: "Bestand" },
        { key: "avg_complexity", label: "Gem." },
        { key: "max", label: "Max" },
        { key: "blocks", label: "Blocks" }
      ]
    },
    todos: {
      title: "TODO / FIXME",
      columns: [
        { key: "file", label: "Bestand" },
        { key: "todo", label: "TODO" },
        { key: "fixme", label: "FIXME" },
        { key: "total", label: "Totaal" }
      ]
    },
    blame: {
      title: "Contributors",
      columns: [
        { key: "author", label: "Auteur" },
        { key: "commits", label: "Commits" }
      ]
    },
    coverage: {
      title: "Test coverage (indicatief)",
      columns: [
        { key: "module", label: "Module" },
        {
          key: "has_test",
          label: "Test",
          render: (r) => r.has_test ? "ja" : "nee"
        }
      ]
    },
    "dead-imports": {
      title: "Modules zonder inkomende imports",
      columns: [
        { key: "module", label: "Module" },
        { key: "incoming", label: "Incoming" }
      ]
    },
    "config-drift": {
      title: "Config bestanden",
      columns: [
        { key: "path", label: "Pad" },
        { key: "size", label: "Bytes" }
      ]
    },
    "session-stats": {
      title: "Session DB",
      columns: [
        { key: "table", label: "Tabel" },
        { key: "rows", label: "Rijen" }
      ]
    }
  };
  function CategoryNav({ categories, tab, setTab, menuOpen, setMenuOpen }) {
    return h10(
      "div",
      { className: "codebase-viz-tabs" },
      categories.map(
        (cat) => h10(
          "div",
          {
            key: cat.id,
            className: "codebase-viz-category" + (menuOpen === cat.id ? " open" : ""),
            onMouseEnter: () => setMenuOpen(cat.id),
            onMouseLeave: () => setMenuOpen(null)
          },
          h10("span", { className: "codebase-viz-category-label" }, cat.label, " \u25BE"),
          menuOpen === cat.id && h10(
            "div",
            { className: "codebase-viz-dropdown" },
            cat.tabs.map(
              (t) => h10(
                "button",
                {
                  key: t.id,
                  type: "button",
                  className: "codebase-viz-dropdown-item" + (tab === t.id ? " active" : ""),
                  onClick: () => {
                    setTab(t.id);
                    setMenuOpen(null);
                  }
                },
                t.label
              )
            )
          )
        )
      )
    );
  }
  function parseFetchError(err) {
    if (!err) return "Onbekende fout";
    const msg = String(err.message || err);
    const m = msg.match(/^\d{3}:\s*(.*)$/s);
    if (!m) return msg;
    try {
      const body = JSON.parse(m[1]);
      if (body && typeof body.detail === "string") return body.detail;
    } catch (_e) {
    }
    return m[1] || msg;
  }
  function App() {
    const SDK = window.__HERMES_PLUGIN_SDK__;
    if (!SDK?.fetchJSON || !SDK?.components) {
      return h10("div", { className: "codebase-viz-error" }, "Hermes Plugin SDK niet beschikbaar.");
    }
    const { Button } = SDK.components;
    const [tab, setTab] = import_react12.default.useState("sunburst");
    const [menuOpen, setMenuOpen] = import_react12.default.useState(null);
    const d3Ready = useD3Loader();
    const isSearch = tab === "search";
    const path = isSearch ? null : TAB_MAP[tab] || "/structure";
    const { data, error, loading } = usePluginFetch(path, [tab]);
    const currentCat = CATEGORIES.find((c) => c.tabs.some((t) => t.id === tab));
    const activeLabel = currentCat ? `${currentCat.label} \u203A ${currentCat.tabs.find((t) => t.id === tab)?.label}` : tab;
    const shell = (content2) => h10(
      "div",
      { className: "codebase-viz-container" },
      h10(CategoryNav, { categories: CATEGORIES, tab, setTab, menuOpen, setMenuOpen }),
      h10("div", { className: "codebase-viz-active-label" }, activeLabel),
      h10("div", { className: "codebase-viz-content" }, content2)
    );
    if (tab === "search") {
      return shell(h10(SearchTab));
    }
    if (error || data?.fallback) {
      return shell(
        h10(
          "div",
          { className: "codebase-viz-error" },
          h10("p", null, parseFetchError(error) || data?.error || "Scan mislukt"),
          h10(
            Button,
            {
              variant: "outline",
              size: "sm",
              onClick: () => postForceScan().then(() => window.location.reload())
            },
            "Opnieuw proberen"
          )
        )
      );
    }
    if (loading || !data) {
      return shell(
        h10(
          "p",
          { className: "codebase-viz-loading" },
          tab === "sunburst" || tab === "treemap" ? "Scannen... (pygount)" : tab === "force-graph" ? "Analyseer imports..." : "Laden..."
        )
      );
    }
    if (tab === "sunburst" && data.tree && !data.tree.children?.length) {
      return shell(
        h10(
          "div",
          { className: "codebase-viz-empty" },
          h10("p", null, "Geen bestanden gevonden in de repo."),
          h10(
            "p",
            { className: "codebase-viz-hint" },
            "Zet CODEBASE_VIZ_REPO naar je git-root en herstart het dashboard."
          )
        )
      );
    }
    let content;
    switch (tab) {
      case "sunburst":
        content = !d3Ready ? h10("p", { className: "codebase-viz-loading" }, "D3 laden...") : h10(SunburstChart, { data });
        break;
      case "force-graph":
        if (!d3Ready) {
          content = h10("p", { className: "codebase-viz-loading" }, "D3 laden...");
        } else if (!data.nodes?.length) {
          content = h10("p", { className: "codebase-viz-empty" }, "Geen Python modules gevonden.");
        } else {
          content = h10(ForceGraph, { data });
        }
        break;
      case "treemap":
        if (!d3Ready) {
          content = h10("p", { className: "codebase-viz-loading" }, "D3 laden...");
        } else if (!data.tree?.children?.length) {
          content = h10("p", { className: "codebase-viz-empty" }, "Geen bestanden voor treemap.");
        } else {
          content = h10(TreemapChart, { data });
        }
        break;
      case "metrics":
        content = h10(MetricsTab, { data });
        break;
      case "health":
        content = h10(HealthTab, { data });
        break;
      case "timeline":
        content = h10(TimelineTab, { data });
        break;
      default: {
        const spec = TABLE_TABS[tab];
        if (spec) {
          content = h10(DataTableTab, {
            data,
            title: spec.title,
            columns: spec.columns
          });
        } else {
          content = h10("p", null, "Tab nog niet ge\xEFmplementeerd.");
        }
      }
    }
    return shell(content);
  }

  // src/index.jsx
  (function() {
    "use strict";
    if (!window.__HERMES_PLUGIN_SDK__) return;
    if (window.__HERMES_PLUGINS__ && typeof window.__HERMES_PLUGINS__.register === "function") {
      window.__HERMES_PLUGINS__.register("codebase-viz", App);
    }
  })();
})();
