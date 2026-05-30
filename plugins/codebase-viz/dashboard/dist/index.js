var CodebaseVizPlugin = (() => {
  // src/react-shim.js
  function getSDK() {
    const SDK2 = typeof window !== "undefined" ? window.__HERMES_PLUGIN_SDK__ : null;
    if (!SDK2?.React) {
      throw new Error("Hermes Plugin SDK React is not available");
    }
    if (!SDK2.hooks?.useEffect || !SDK2.hooks?.useRef) {
      throw new Error("Hermes Plugin SDK hooks are not available");
    }
    return SDK2;
  }
  var SDK = getSDK();
  var React = SDK.React;
  var react_shim_default = React;
  var useEffect = SDK.hooks.useEffect;
  var useRef = SDK.hooks.useRef;
  var useState = SDK.hooks.useState;
  var useMemo = SDK.hooks.useMemo;
  var useCallback = SDK.hooks.useCallback;

  // src/SunburstChart.jsx
  var COLOR_MAP = {
    Python: "#4CAF50",
    TypeScript: "#64B5F6",
    JavaScript: "#FFD54F",
    HTML: "#FFAB91",
    CSS: "#80DEEA",
    Shell: "#AED581",
    Markdown: "#90CAF9",
    YAML: "#A5D6A7",
    JSON: "#BDBDBD",
    Dockerfile: "#4FC3F7"
  };
  var COLOR_DEFAULT = "#90A4AE";
  function textColorForBackground(hex) {
    if (!hex || hex.startsWith("hsl")) return "#fff";
    const r = parseInt(hex.slice(1, 3), 16) || 0;
    const g = parseInt(hex.slice(3, 5), 16) || 0;
    const b = parseInt(hex.slice(5, 7), 16) || 0;
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.55 ? "#0f0f0f" : "#ffffff";
  }
  function centroidLabel(d) {
    const r = (d.y0 + d.y1) / 2;
    const a = (d.x0 + d.x1) / 2 - Math.PI / 2;
    return {
      x: r * Math.cos(a),
      y: r * Math.sin(a),
      rotation: a * 180 / Math.PI + (a > Math.PI / 2 ? 180 : 0),
      anchor: a > Math.PI / 2 ? "end" : "start"
    };
  }
  function SunburstChart({ data }) {
    const svgRef = useRef(null);
    const containerRef = useRef(null);
    const [size, setSize] = useState({ w: 0, h: 0 });
    const [tooltip, setTooltip] = useState(null);
    const [currentZoom, setCurrentZoom] = useState(null);
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return void 0;
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
      svg.selectAll("*").remove();
      const width = size.w || svgRef.current.clientWidth || 800;
      const height = size.h || svgRef.current.clientHeight || 600;
      const radius = Math.min(width, height) / 2;
      const root = d3.hierarchy(data.tree).sum((d) => Math.max(d.loc || 0, 1));
      d3.partition().size([2 * Math.PI, radius])(root);
      const g = svg.append("g").attr("transform", `translate(${width / 2},${height / 2})`);
      const arc = d3.arc().startAngle((d) => d.x0).endAngle((d) => d.x1).innerRadius((d) => d.y0).outerRadius((d) => d.y1);
      const descendants = root.descendants().filter((d) => d.depth > 0);
      const paths = g.selectAll("path").data(descendants).enter().append("path").attr("d", arc).attr("fill", (d) => COLOR_MAP[d.data.language] || COLOR_DEFAULT).attr("opacity", 0.85).attr("stroke", "hsl(var(--background))").attr("stroke-width", 1).style("cursor", "pointer");
      paths.on("click", function(event, d) {
        event.stopPropagation();
        const current = currentZoom;
        if (current && current === d) {
          resetZoom();
          return;
        }
        setCurrentZoom(d);
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
      }).on("mousemove", function(event, d) {
        event.stopPropagation();
        const lang = d.data.language || "?";
        setTooltip({
          x: event.clientX + 12,
          y: event.clientY - 8,
          html: `<strong>${d.data.name}</strong><br/>${lang}<br/>${d.value} LOC`
        });
      }).on("mouseleave", function() {
        setTooltip(null);
      }).on("mouseover", function(_event, d) {
        const lang = d.data.language;
        d3.select(this).attr("opacity", 1).attr("stroke-width", 2);
        if (lang) {
          paths.attr("opacity", (n) => n.data.language === lang ? 1 : 0.35);
        }
      }).on("mouseout", function() {
        paths.attr("opacity", 0.85).attr("stroke-width", 1);
        setTooltip(null);
      });
      const labelG = g.append("g").attr("class", "labels");
      labelG.selectAll("text").data(descendants.filter((d) => {
        const arcLen = (d.y1 - d.y0) * ((d.x1 - d.x0) / 2);
        return arcLen > 18 && d.x1 - d.x0 > 0.12;
      })).join("text").attr("transform", (d) => {
        const c = centroidLabel(d);
        return `translate(${c.x},${c.y}) rotate(${c.rotation})`;
      }).attr("text-anchor", (d) => centroidLabel(d).anchor).attr("dy", "0.35em").attr("font-size", (d) => {
        const depthScale = Math.max(7, 11 - d.depth);
        return depthScale + "px";
      }).attr("fill", (d) => textColorForBackground(COLOR_MAP[d.data.language] || COLOR_DEFAULT)).style("pointer-events", "none").style("text-shadow", "0 1px 2px rgba(0,0,0,0.4)").text((d) => {
        const arcLen = (d.y1 - d.y0) * ((d.x1 - d.x0) / 2);
        const maxChars = Math.floor(arcLen / 4.5);
        const name = d.data.name;
        return name.length > maxChars && maxChars > 1 ? name.substring(0, maxChars) + "\u2026" : name;
      });
      function resetZoom() {
        setCurrentZoom(null);
        g.transition().duration(750).attr("transform", `translate(${width / 2},${height / 2})`);
        paths.transition().duration(750).attr("d", arc);
      }
      svg.on("click", () => {
        resetZoom();
      });
    }, [data, size]);
    return react_shim_default.createElement("div", {
      ref: containerRef,
      style: { width: "100%", height: "100%", minHeight: "300px", position: "relative" },
      children: [
        react_shim_default.createElement("svg", {
          key: "svg",
          ref: svgRef,
          className: "codebase-viz-sunburst",
          style: { width: "100%", height: "100%", display: "block" }
        }),
        tooltip && react_shim_default.createElement("div", {
          key: "tooltip",
          style: {
            position: "fixed",
            left: tooltip.x,
            top: tooltip.y,
            background: "hsl(var(--popover, var(--background)))",
            color: "hsl(var(--popover-foreground, var(--foreground)))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "0.4rem",
            padding: "0.35rem 0.6rem",
            fontSize: "0.78rem",
            lineHeight: 1.4,
            pointerEvents: "none",
            boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
            zIndex: 2e3,
            maxWidth: "16rem"
          },
          dangerouslySetInnerHTML: { __html: tooltip.html }
        })
      ]
    });
  }

  // src/usePluginFetch.js
  var API = "/api/plugins/codebase-viz";
  var LOG = "[codebase-viz]";
  function notifyScanRepoFromBody(body) {
    if (!body || typeof body !== "object") return;
    if (!body.repo_path && !body.repo_label) return;
    window.dispatchEvent(
      new CustomEvent("codebase-viz:repo-meta", {
        detail: { repo_path: body.repo_path, repo_label: body.repo_label }
      })
    );
  }
  function usePluginFetch(path, deps = [], refreshToken = 0) {
    const SDK2 = window.__HERMES_PLUGIN_SDK__;
    const [data, setData] = react_shim_default.useState(null);
    const [error, setError] = react_shim_default.useState(null);
    const [loading, setLoading] = react_shim_default.useState(true);
    react_shim_default.useEffect(() => {
      if (!SDK2?.fetchJSON || !path) return void 0;
      const ac = new AbortController();
      setLoading(true);
      setError(null);
      const url = `${API}${path}`;
      console.info(LOG, "fetch start", url);
      SDK2.fetchJSON(url, { signal: ac.signal }).then((body) => {
        if (!ac.signal.aborted) {
          console.info(LOG, "fetch ok", url, {
            fallback: body?.fallback,
            error: body?.error,
            keys: body && typeof body === "object" ? Object.keys(body) : []
          });
          setData(body);
          notifyScanRepoFromBody(body);
        }
      }).catch((err) => {
        if (err?.name !== "AbortError" && !ac.signal.aborted) {
          console.error(LOG, "fetch fail", url, err);
          setError(err);
        }
      }).finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
      return () => ac.abort();
    }, [path, refreshToken, ...deps]);
    return { data, error, loading };
  }
  async function postForceScan() {
    const SDK2 = window.__HERMES_PLUGIN_SDK__;
    if (!SDK2?.fetchJSON) return;
    await SDK2.fetchJSON(`${API}/force-scan`, { method: "POST" });
  }
  function useD3Loader() {
    const [ready, setReady] = react_shim_default.useState(!!window.d3);
    react_shim_default.useEffect(() => {
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
  var h = react_shim_default.createElement;
  function HistoryChart({ data }) {
    const svgRef = react_shim_default.useRef(null);
    const points = data?.points || [];
    react_shim_default.useEffect(() => {
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
  var h2 = react_shim_default.createElement;
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
  var h3 = react_shim_default.createElement;
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
  var h4 = react_shim_default.createElement;
  function useFileWatcher(opts = {}) {
    const { onEvent, reconnectDelay = 3e3 } = opts;
    const [connected, setConnected] = react_shim_default.useState(false);
    const [lastEvent, setLastEvent] = react_shim_default.useState(null);
    const [reconnect, setReconnect] = react_shim_default.useState(0);
    react_shim_default.useEffect(() => {
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
    const [ripple, setRipple] = react_shim_default.useState(null);
    react_shim_default.useEffect(() => {
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
  var h5 = react_shim_default.createElement;
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
    const svgRef = react_shim_default.useRef(null);
    const containerRef = react_shim_default.useRef(null);
    const simRef = react_shim_default.useRef(null);
    const zoomBehaviorRef = react_shim_default.useRef(null);
    const [search, setSearch] = react_shim_default.useState("");
    const [inspector, setInspector] = react_shim_default.useState(null);
    const [size, setSize] = react_shim_default.useState({ w: 0, h: 0 });
    const [tooltip, setTooltip] = react_shim_default.useState(null);
    const [hoveredNode, setHoveredNode] = react_shim_default.useState(null);
    const { connected, lastEvent } = useFileWatcher();
    const ripple = useRippleAnimation(lastEvent);
    const graph = react_shim_default.useMemo(() => buildGraph(data, search), [data, search]);
    react_shim_default.useEffect(() => {
      const onEscape = () => setInspector(null);
      window.addEventListener("codebase-viz:escape", onEscape);
      return () => window.removeEventListener("codebase-viz:escape", onEscape);
    }, []);
    react_shim_default.useEffect(() => {
      const container = containerRef.current;
      if (!container) return void 0;
      const ro = new ResizeObserver(() => {
        setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 400) });
      });
      ro.observe(container);
      setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 400) });
      return () => ro.disconnect();
    }, []);
    react_shim_default.useEffect(() => {
      const svg = svgRef.current;
      if (!svg || !data?.nodes?.length || size.w < 10) return void 0;
      const d3 = window.d3;
      if (!d3) return void 0;
      const { nodes, links } = graph;
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
      zoomBehaviorRef.current = zoom;
      d3.select(svg).call(zoom).on("dblclick.zoom", null);
      const simulation = d3.forceSimulation(nodes).force("link", d3.forceLink(links).id((d) => d.id).distance(80)).force("charge", d3.forceManyBody().strength(-250)).force("center", d3.forceCenter(width / 2, height / 2)).force("collision", d3.forceCollide().radius(18));
      simRef.current = simulation;
      const link = g.append("g").attr("stroke-linecap", "round").selectAll("line").data(links).join("line").attr("stroke", "hsl(var(--muted-foreground) / 0.35)").attr("stroke-width", 1).attr("stroke-dasharray", (d) => d.type === "from_import" ? "3,2" : "0").style("pointer-events", "none");
      const node = g.append("g").selectAll("circle").data(nodes).join("circle").attr("r", (d) => {
        const deg = links.filter((l) => l.source === d.id || l.target === d.id).length;
        return 5 + Math.min(deg, 8);
      }).attr("fill", (d) => {
        if (d.id === hoveredNode) return "hsl(var(--primary))";
        return "hsl(var(--muted-foreground) / 0.6)";
      }).attr("stroke", (d) => d.id === hoveredNode ? "hsl(var(--primary))" : "hsl(var(--border))").attr("stroke-width", (d) => d.id === hoveredNode ? 2.5 : 1).style("cursor", "pointer").style("transition", "fill 0.2s, stroke 0.2s").call(
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
      ).on("click", (event, d) => {
        event.stopPropagation();
        setInspector(d.id);
      }).on("mouseenter", function(event, d) {
        if (d.x == null || d.y == null) return;
        setHoveredNode(d.id);
        setTooltip({
          x: event.clientX + 10,
          y: event.clientY - 10,
          html: `<strong>${d.id}</strong>`
        });
        g.append("circle").attr("class", "codebase-viz-hover-pulse").attr("cx", d.x).attr("cy", d.y).attr("r", 5).attr("fill", "none").attr("stroke", "hsl(var(--primary))").attr("stroke-width", 1.5).attr("opacity", 0.85).transition().duration(500).attr("r", 24).attr("opacity", 0).remove();
      }).on("mousemove", function(event, d) {
        setTooltip({
          x: event.clientX + 10,
          y: event.clientY - 10,
          html: `<strong>${d.id}</strong>`
        });
      }).on("mouseleave", function() {
        setHoveredNode(null);
        setTooltip(null);
      });
      const label = g.append("g").selectAll("text").data(nodes).join("text").text((d) => d.id.split(".").pop()).attr("font-size", "9px").attr("dx", 10).attr("dy", 3).attr("fill", "hsl(var(--foreground) / 0.75)").style("pointer-events", "none").style("opacity", (d) => d.id === hoveredNode || d.id === inspector ? 1 : 0).style("transition", "opacity 0.2s");
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
      const flyToSearchMatch = () => {
        const q = search.trim().toLowerCase();
        if (!q || !zoomBehaviorRef.current) return;
        const match = nodes.find((n) => n.id.toLowerCase().includes(q));
        if (!match || match.x == null || match.y == null) return;
        const scale = 1.75;
        const transform = d3.zoomIdentity.translate(width / 2 - match.x * scale, height / 2 - match.y * scale).scale(scale);
        d3.select(svg).transition().duration(650).call(zoomBehaviorRef.current.transform, transform);
      };
      if (search.trim()) {
        simulation.on("end.fly", flyToSearchMatch);
        if (simulation.alpha() < 0.05) flyToSearchMatch();
      }
      simulation.on("tick", () => {
        link.attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y).attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
        node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
        label.attr("x", (d) => d.x).attr("y", (d) => d.y);
      });
      return () => {
        simulation.on("end.fly", null);
        simulation.stop();
        simRef.current = null;
        zoomBehaviorRef.current = null;
      };
    }, [graph, ripple, size, hoveredNode, inspector]);
    const edgeList = Array.isArray(data?.edges) ? data.edges : [];
    const inEdges = inspector ? edgeList.filter((e) => e.target === inspector).slice(0, 20) : [];
    const outEdges = inspector ? edgeList.filter((e) => e.source === inspector).slice(0, 20) : [];
    return h5(
      "div",
      { style: { display: "flex", flexDirection: "column", height: "100%", position: "relative" } },
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
      graph.capped && h5(
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
        style: { flex: 1, minHeight: 0, overflow: "hidden", position: "relative" },
        children: h5("svg", { ref: svgRef, style: { width: "100%", height: "100%", display: "block" } })
      }),
      tooltip && h5("div", {
        style: {
          position: "fixed",
          left: tooltip.x,
          top: tooltip.y,
          background: "hsl(var(--popover, var(--background)))",
          color: "hsl(var(--popover-foreground, var(--foreground)))",
          border: "1px solid hsl(var(--border))",
          borderRadius: "0.4rem",
          padding: "0.35rem 0.6rem",
          fontSize: "0.78rem",
          lineHeight: 1.4,
          pointerEvents: "none",
          boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
          zIndex: 2e3,
          maxWidth: "16rem"
        },
        dangerouslySetInnerHTML: { __html: tooltip.html }
      })
    );
  }

  // src/TreemapChart.jsx
  var h6 = react_shim_default.createElement;
  var LANG_COLORS = {
    python: "#4CAF50",
    javascript: "#FFD54F",
    typescript: "#64B5F6",
    jsx: "#81D4FA",
    tsx: "#64B5F6",
    markdown: "#90CAF9",
    json: "#BDBDBD",
    yaml: "#A5D6A7",
    html: "#FFAB91",
    css: "#80DEEA",
    shell: "#AED581",
    powershell: "#90A4AE",
    sql: "#FFB74D",
    dockerfile: "#4FC3F7",
    makefile: "#C5E1A5",
    rust: "#FFCC80",
    go: "#4DD0E1",
    "c#": "#A5D6A7",
    ruby: "#EF9A9A",
    php: "#CE93D8",
    java: "#FFB74D",
    kotlin: "#B39DDB",
    scala: "#EF9A9A",
    swift: "#FFAB91"
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
  function textColorForBackground2(hex) {
    if (!hex || hex.startsWith("hsl")) return "#fff";
    const r = parseInt(hex.slice(1, 3), 16) || 0;
    const g = parseInt(hex.slice(3, 5), 16) || 0;
    const b = parseInt(hex.slice(5, 7), 16) || 0;
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.55 ? "#0f0f0f" : "#ffffff";
  }
  function TreemapChart({ data }) {
    const svgRef = react_shim_default.useRef(null);
    const containerRef = react_shim_default.useRef(null);
    const [zoomStack, setZoomStack] = react_shim_default.useState([]);
    const [size, setSize] = react_shim_default.useState({ w: 0, h: 0 });
    const [tooltip, setTooltip] = react_shim_default.useState(null);
    const tooltipRef = react_shim_default.useRef(null);
    const treeData = data?.tree || { name: "root", children: [], loc: 0 };
    const currentData = zoomStack.length > 0 ? zoomStack[zoomStack.length - 1] : treeData;
    function zoomTo(node) {
      setZoomStack((prev) => [...prev, node]);
    }
    function zoomOut() {
      setZoomStack((prev) => prev.length > 1 ? prev.slice(0, -1) : []);
    }
    react_shim_default.useEffect(() => {
      const container = containerRef.current;
      if (!container) return void 0;
      const ro = new ResizeObserver(() => {
        setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 300) });
      });
      ro.observe(container);
      setSize({ w: container.clientWidth, h: Math.max(container.clientHeight, 300) });
      return () => ro.disconnect();
    }, []);
    react_shim_default.useEffect(() => {
      const svg = svgRef.current;
      if (!svg || size.w < 10) return void 0;
      const d3 = window.d3;
      if (!d3) return void 0;
      const width = size.w;
      const height = size.h;
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
      const cellSel = g.selectAll("g.cell").data(cells).join("g").attr("class", "cell");
      cellSel.append("rect").attr("x", (d) => d.x0).attr("y", (d) => d.y0).attr("width", (d) => Math.max(0, d.x1 - d.x0)).attr("height", (d) => Math.max(0, d.y1 - d.y0)).attr(
        "fill",
        (d) => d.data.type === "dir" ? "hsl(var(--muted-foreground) / 0.25)" : getColor(d.data.language, d3)
      ).attr("stroke", "hsl(var(--background))").attr("stroke-width", 1).style(
        "cursor",
        (d) => d.data.type === "dir" && d.data._raw?.children?.length ? "pointer" : "default"
      ).on("click", (_event, d) => {
        if (d.data.type === "dir" && d.data._raw?.children?.length) {
          zoomTo(d.data._raw);
        }
      }).on("mousemove", function(event, d) {
        event.stopPropagation();
        const kind = d.data.type === "dir" ? "map" : d.data.language || "?";
        setTooltip({
          x: event.clientX + 12,
          y: event.clientY - 8,
          html: `<strong>${d.data.name}</strong><br/>${kind}<br/>${d.value} LOC`
        });
      }).on("mouseleave", function() {
        setTooltip(null);
      });
      cellSel.append("text").attr("class", "label").attr("x", (d) => d.x0 + 3).attr("y", (d) => d.y0 + 12).attr("font-size", (d) => {
        const h12 = d.y1 - d.y0;
        if (h12 < 14) return "0px";
        return Math.min(12, Math.max(9, h12 / 3.5)) + "px";
      }).attr("fill", (d) => {
        if (d.data.type === "dir") return "hsl(var(--foreground))";
        return textColorForBackground2(getColor(d.data.language, d3));
      }).style("pointer-events", "none").style(
        "text-shadow",
        (d) => d.data.type === "dir" ? "none" : "0 1px 2px rgba(0,0,0,0.35)"
      ).style("opacity", (d) => {
        const area = (d.x1 - d.x0) * (d.y1 - d.y0);
        return area < 200 ? 0 : 1;
      }).each(function(d) {
        const w = d.x1 - d.x0;
        const h12 = d.y1 - d.y0;
        if (w < 24 || h12 < 14) {
          d3.select(this).text("");
          return;
        }
        const label = d.data.type === "dir" ? `${d.data.name}/` : d.data.name;
        const maxChars = Math.floor((w - 6) / (label.length > 10 ? 5.5 : 6));
        const text = label.length > maxChars && maxChars > 0 ? label.substring(0, maxChars) + "\u2026" : label;
        d3.select(this).text(text);
      });
      return void 0;
    }, [currentData, size]);
    const crumbs = zoomStack.length ? zoomStack : [treeData];
    return h6(
      "div",
      { style: { display: "flex", flexDirection: "column", height: "100%", position: "relative" } },
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
        style: { flex: 1, minHeight: 0, overflow: "hidden", position: "relative" },
        children: h6("svg", { ref: svgRef, style: { width: "100%", height: "100%", display: "block" } })
      }),
      tooltip && h6("div", {
        ref: tooltipRef,
        style: {
          position: "fixed",
          left: tooltip.x,
          top: tooltip.y,
          background: "hsl(var(--popover, var(--background)))",
          color: "hsl(var(--popover-foreground, var(--foreground)))",
          border: "1px solid hsl(var(--border))",
          borderRadius: "0.4rem",
          padding: "0.35rem 0.6rem",
          fontSize: "0.78rem",
          lineHeight: 1.4,
          pointerEvents: "none",
          boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
          zIndex: 2e3,
          maxWidth: "16rem"
        },
        dangerouslySetInnerHTML: { __html: tooltip.html }
      })
    );
  }

  // src/DataTableTab.jsx
  var h7 = react_shim_default.createElement;
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
  var h8 = react_shim_default.createElement;
  function SearchTab() {
    const [query, setQuery] = react_shim_default.useState("");
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
  var h9 = react_shim_default.createElement;
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

  // src/useKeyboardShortcuts.js
  var SHORTCUT_TABS = [
    "sunburst",
    "force-graph",
    "treemap",
    "metrics",
    "churn",
    "age-map",
    "complexity",
    "todos",
    "blame",
    "coverage"
  ];
  function isTypingTarget(target) {
    if (!target) return false;
    const tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
  }
  function useKeyboardShortcuts({ setTab, onRefresh }) {
    react_shim_default.useEffect(() => {
      const handler = (e) => {
        if (isTypingTarget(e.target)) return;
        if (e.key >= "1" && e.key <= "9") {
          const tab = SHORTCUT_TABS[parseInt(e.key, 10) - 1];
          if (tab) {
            e.preventDefault();
            setTab(tab);
          }
          return;
        }
        if (e.key === "0") {
          e.preventDefault();
          setTab("coverage");
          return;
        }
        if (e.key === "Escape") {
          window.dispatchEvent(new CustomEvent("codebase-viz:escape"));
          return;
        }
        if (e.key === "r" && !e.ctrlKey && !e.metaKey && !e.altKey) {
          e.preventDefault();
          onRefresh();
        }
      };
      window.addEventListener("keydown", handler);
      return () => window.removeEventListener("keydown", handler);
    }, [setTab, onRefresh]);
  }

  // src/useScanProgress.js
  var API2 = "/api/plugins/codebase-viz";
  var LOG2 = "[codebase-viz]";
  function tabDetail(tab) {
    if (tab === "sunburst" || tab === "treemap") return "LOC tellen (pygount)\u2026";
    if (tab === "force-graph" || tab === "dependencies") return "Python-imports analyseren\u2026";
    if (tab === "metrics" || tab === "summary") return "Metrics samenstellen\u2026";
    return "Gegevens laden\u2026";
  }
  function isScanStatusPayload(body) {
    return body && typeof body === "object" && typeof body.progress === "number" && "phase" in body;
  }
  function mergeScanContext(prev, body, health, fetchBody) {
    const next = { ...prev };
    if (fetchBody?.repo_path) next.repoPath = fetchBody.repo_path;
    if (fetchBody?.repo_label) next.repoLabel = fetchBody.repo_label;
    if (health?.repo_path) next.repoPath = health.repo_path;
    if (health?.pygount_timeout_sec != null) next.timeoutSec = health.pygount_timeout_sec;
    if (health?.scan_mode) next.scanMode = health.scan_mode;
    if (body?.repo_path) next.repoPath = body.repo_path;
    if (body?.repo_label) next.repoLabel = body.repo_label;
    if (body?.timeout_sec != null) next.timeoutSec = body.timeout_sec;
    if (body?.phase) next.phase = body.phase;
    if (body?.scan_mode) next.scanMode = body.scan_mode;
    if (typeof body?.served_from_cache === "boolean") next.servedFromCache = body.served_from_cache;
    if (typeof body?.stale_age_sec === "number") next.staleAgeSec = body.stale_age_sec;
    if (typeof body?.refresh_in_background === "boolean") {
      next.refreshInBackground = body.refresh_in_background;
    } else if (typeof body?.refresh?.running === "boolean") {
      next.refreshInBackground = body.refresh.running;
    }
    return next;
  }
  function useScanProgress(active, tab) {
    const SDK2 = window.__HERMES_PLUGIN_SDK__;
    const startRef = react_shim_default.useRef(0);
    const [elapsedSec, setElapsedSec] = react_shim_default.useState(0);
    const [serverStatus, setServerStatus] = react_shim_default.useState(null);
    const [useLocalOnly, setUseLocalOnly] = react_shim_default.useState(false);
    const [legacyBackend, setLegacyBackend] = react_shim_default.useState(false);
    const [apiPath, setApiPath] = react_shim_default.useState("");
    const [serverVersion, setServerVersion] = react_shim_default.useState("");
    const [scanContext, setScanContext] = react_shim_default.useState({
      repoPath: "",
      repoLabel: "",
      timeoutSec: null,
      phase: "",
      scanMode: "",
      servedFromCache: null,
      staleAgeSec: null,
      refreshInBackground: false
    });
    const warnedRef = react_shim_default.useRef(false);
    const sdkRef = react_shim_default.useRef(SDK2);
    sdkRef.current = SDK2;
    react_shim_default.useEffect(() => {
      if (!active) {
        startRef.current = 0;
        setElapsedSec(0);
        setServerStatus(null);
        setUseLocalOnly(false);
        setLegacyBackend(false);
        setApiPath("");
        setServerVersion("");
        setScanContext({
          repoPath: "",
          repoLabel: "",
          timeoutSec: null,
          phase: "",
          scanMode: "",
          servedFromCache: null,
          staleAgeSec: null,
          refreshInBackground: false
        });
        warnedRef.current = false;
        return void 0;
      }
      startRef.current = Date.now();
      const tick = window.setInterval(() => {
        setElapsedSec(Math.floor((Date.now() - startRef.current) / 1e3));
      }, 1e3);
      return () => window.clearInterval(tick);
    }, [active, tab]);
    react_shim_default.useEffect(() => {
      function onRepoMeta(ev) {
        const d = ev?.detail;
        if (!d) return;
        setScanContext(
          (prev) => mergeScanContext(prev, d, null, d)
        );
      }
      window.addEventListener("codebase-viz:repo-meta", onRepoMeta);
      return () => window.removeEventListener("codebase-viz:repo-meta", onRepoMeta);
    }, []);
    react_shim_default.useEffect(() => {
      const fetchJSON = sdkRef.current?.fetchJSON;
      if (!active || !fetchJSON) return void 0;
      let cancelled = false;
      let pollId = null;
      const stopPolling = () => {
        if (pollId != null) {
          window.clearInterval(pollId);
          pollId = null;
        }
      };
      const enableLocal = (reason) => {
        stopPolling();
        if (!warnedRef.current) {
          warnedRef.current = true;
          console.info(
            LOG2,
            "voortgang via lokale timer",
            reason || "(herstart dashboard met nieuwste plugin_api voor server-status)"
          );
        }
        setUseLocalOnly(true);
      };
      const pollScanStatus = () => {
        fetchJSON(`${API2}/scan-status`).then((body) => {
          if (cancelled) return;
          if (isScanStatusPayload(body)) {
            setServerStatus(body);
            setScanContext((prev) => mergeScanContext(prev, body, null));
            if (body.phase === "idle" || body.phase === "done") {
              if (pollId != null) {
                window.clearInterval(pollId);
                pollId = window.setInterval(pollScanStatus, 5e3);
              }
            }
          } else {
            enableLocal("scan-status antwoord ongeldig");
          }
        }).catch((err) => {
          if (!cancelled) enableLocal(err?.message || String(err));
        });
      };
      fetchJSON(`${API2}/health`).then((health) => {
        if (cancelled) return;
        if (typeof health?.version === "string") {
          setServerVersion(health.version);
        }
        if (typeof health?.plugin_api_path === "string") {
          setApiPath(health.plugin_api_path);
        }
        setScanContext((prev) => mergeScanContext(prev, null, health));
        if (typeof health?.pygount_timeout_sec === "number") {
          setLegacyBackend(false);
          pollScanStatus();
          pollId = window.setInterval(pollScanStatus, 800);
        } else {
          setLegacyBackend(true);
          enableLocal("oude plugin_api (geen pygount_timeout_sec in /health)");
        }
      }).catch(() => {
        if (!cancelled) enableLocal("health niet bereikbaar");
      });
      return () => {
        cancelled = true;
        stopPolling();
      };
    }, [active, tab]);
    const detail = useLocalOnly ? tabDetail(tab) : serverStatus?.detail || tabDetail(tab);
    const progress = useLocalOnly ? Math.min(90, 10 + elapsedSec * 4) : typeof serverStatus?.progress === "number" ? serverStatus.progress : Math.min(90, 10 + elapsedSec * 4);
    const elapsed = !useLocalOnly && serverStatus?.elapsed_sec != null ? `${serverStatus.elapsed_sec}s` : elapsedSec > 0 ? `${elapsedSec}s` : "";
    const maxSec = scanContext.timeoutSec;
    const elapsedWithMax = elapsed && maxSec != null ? `${elapsed} / max ${maxSec}s` : elapsed;
    return {
      detail,
      progress,
      elapsed: elapsedWithMax,
      busy: useLocalOnly ? elapsedSec < 600 : serverStatus == null ? true : serverStatus.busy !== false,
      legacyApi: legacyBackend,
      apiPath,
      serverVersion,
      repoPath: scanContext.repoPath,
      repoLabel: scanContext.repoLabel || scanContext.repoPath,
      timeoutSec: scanContext.timeoutSec,
      phase: scanContext.phase || serverStatus?.phase || "",
      scanMode: scanContext.scanMode,
      servedFromCache: scanContext.servedFromCache,
      staleAgeSec: scanContext.staleAgeSec,
      refreshInBackground: scanContext.refreshInBackground
    };
  }

  // src/ScanProgress.jsx
  var h10 = react_shim_default.createElement;
  var LOG3 = "[codebase-viz]";
  function ScanProgress({ active, tab }) {
    const {
      detail,
      progress,
      elapsed,
      busy,
      legacyApi,
      apiPath,
      serverVersion,
      repoPath,
      repoLabel,
      timeoutSec,
      phase,
      scanMode,
      servedFromCache,
      staleAgeSec,
      refreshInBackground
    } = useScanProgress(active, tab);
    const pct = busy ? Math.max(12, Math.min(98, progress)) : 100;
    const loggedRef = react_shim_default.useRef(false);
    const expectedHint = timeoutSec != null ? `v2.5.0 / ${timeoutSec}s` : "v2.5.0";
    react_shim_default.useEffect(() => {
      if (!active) {
        loggedRef.current = false;
        return;
      }
      if (loggedRef.current) return;
      if (!repoPath && !repoLabel && timeoutSec == null) return;
      loggedRef.current = true;
      console.info(LOG3, "scan gestart", { tab, detail, repoLabel, repoPath });
    }, [active, tab, detail, repoLabel, repoPath, timeoutSec]);
    const scanTarget = repoLabel || repoPath;
    const phaseKey = phase || detail;
    return h10(
      "div",
      {
        className: "codebase-viz-scan-progress" + (busy ? " codebase-viz-scan-progress--busy" : ""),
        role: "status",
        "aria-live": "polite"
      },
      legacyApi ? h10(
        "p",
        { className: "codebase-viz-legacy-hint" },
        apiPath ? [
          "Verouderde plugin-backend (pygount stopt te vroeg). Geladen vanaf: ",
          h10("code", { className: "codebase-viz-api-path", key: "api" }, apiPath),
          " \u2014 verwijder of update die installatie, of start via ",
          h10("code", { key: "bat" }, "start_hermes.bat"),
          " en hard-refresh (Ctrl+Shift+R)."
        ] : [
          "Verouderde plugin-backend",
          serverVersion ? ` (v${serverVersion})` : "",
          ` \u2014 verwacht ${expectedHint}. Controleer `,
          h10("code", { key: "w1" }, "%LOCALAPPDATA%\\hermes\\plugins\\codebase-viz"),
          " of ",
          h10("code", { key: "w2" }, "%USERPROFILE%\\.hermes\\plugins\\codebase-viz"),
          ", of voer ",
          h10("code", { key: "fix" }, "start_hermes.bat"),
          " uit en hard-refresh."
        ]
      ) : null,
      h10(
        "div",
        {
          className: "codebase-viz-progress-track",
          role: "progressbar",
          "aria-valuemin": 0,
          "aria-valuemax": 100,
          "aria-valuenow": pct,
          "aria-label": detail
        },
        h10("div", {
          className: "codebase-viz-progress-bar" + (busy && pct < 90 ? " indeterminate" : ""),
          style: { width: `${pct}%` }
        })
      ),
      h10(
        "div",
        { className: "codebase-viz-progress-meta", key: phaseKey },
        h10("span", { className: "codebase-viz-progress-detail" }, detail),
        elapsed ? h10("span", { className: "codebase-viz-progress-elapsed" }, elapsed) : busy ? h10("span", { className: "codebase-viz-progress-elapsed" }, "\u2026") : null
      ),
      h10(
        "div",
        { className: "codebase-viz-swr-meta" },
        scanMode ? h10("span", { className: "codebase-viz-swr-pill" }, `mode:${scanMode}`) : null,
        typeof servedFromCache === "boolean" ? h10(
          "span",
          { className: "codebase-viz-swr-pill" },
          servedFromCache ? "cached" : "live"
        ) : null,
        typeof staleAgeSec === "number" ? h10("span", { className: "codebase-viz-swr-pill" }, `stale:${staleAgeSec}s`) : null,
        refreshInBackground ? h10("span", { className: "codebase-viz-swr-pill codebase-viz-swr-pill--active" }, "refreshing") : null
      ),
      scanTarget ? h10(
        "p",
        {
          className: "codebase-viz-scan-target",
          title: repoPath || scanTarget
        },
        busy ? h10("span", { className: "codebase-viz-scan-pulse", "aria-hidden": true }) : null,
        "Scan: ",
        h10("code", null, scanTarget)
      ) : null
    );
  }

  // src/App.jsx
  var h11 = react_shim_default.createElement;
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
    const navRef = react_shim_default.useRef(null);
    react_shim_default.useEffect(() => {
      if (!menuOpen) return void 0;
      function onKey(e) {
        if (e.key === "Escape") setMenuOpen(null);
      }
      function onPointerDown(e) {
        const root = navRef.current;
        if (!root || root.contains(e.target)) return;
        setMenuOpen(null);
      }
      document.addEventListener("keydown", onKey);
      document.addEventListener("pointerdown", onPointerDown);
      return () => {
        document.removeEventListener("keydown", onKey);
        document.removeEventListener("pointerdown", onPointerDown);
      };
    }, [menuOpen, setMenuOpen]);
    return h11(
      "div",
      {
        ref: navRef,
        className: "codebase-viz-nav-shell" + (menuOpen ? " is-menu-open" : "")
      },
      h11(
        "div",
        { className: "codebase-viz-tabs", role: "menubar" },
        categories.map(
          (cat) => h11(
            "div",
            {
              key: cat.id,
              className: "codebase-viz-category" + (menuOpen === cat.id ? " open" : ""),
              role: "none"
            },
            h11(
              "button",
              {
                type: "button",
                className: "codebase-viz-category-trigger",
                "aria-expanded": menuOpen === cat.id,
                "aria-haspopup": "menu",
                onClick: () => setMenuOpen(menuOpen === cat.id ? null : cat.id)
              },
              cat.label,
              " \u25BE"
            ),
            menuOpen === cat.id && h11(
              "div",
              { className: "codebase-viz-dropdown", role: "menu" },
              cat.tabs.map(
                (t) => h11(
                  "button",
                  {
                    key: t.id,
                    type: "button",
                    role: "menuitem",
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
      )
    );
  }
  function parseFetchError(err) {
    if (!err) return "";
    const msg = String(err.message || err.name || err);
    if (!msg || msg === "[object Object]") {
      try {
        return JSON.stringify(err);
      } catch (_e) {
        return "Netwerkfout \u2014 open DevTools \u2192 Network";
      }
    }
    const m = msg.match(/^\d{3}:\s*(.*)$/s);
    if (!m) return msg;
    try {
      const body = JSON.parse(m[1]);
      if (body && typeof body.detail === "string") return body.detail;
      if (body && typeof body.error === "string") return body.error;
    } catch (_e) {
    }
    return m[1] || msg;
  }
  function WarningBanner({ message, onRetry }) {
    const SDK2 = window.__HERMES_PLUGIN_SDK__;
    const { Button } = SDK2?.components || {};
    return h11(
      "div",
      { className: "codebase-viz-warn-banner", role: "alert" },
      h11("p", null, message),
      Button && h11(
        Button,
        { variant: "outline", size: "sm", onClick: onRetry },
        "Opnieuw proberen"
      )
    );
  }
  function App() {
    const SDK2 = window.__HERMES_PLUGIN_SDK__;
    if (!SDK2?.fetchJSON || !SDK2?.components) {
      return h11("div", { className: "codebase-viz-error" }, "Hermes Plugin SDK niet beschikbaar.");
    }
    const { Button } = SDK2.components;
    const [tab, setTab] = react_shim_default.useState("sunburst");
    const [menuOpen, setMenuOpen] = react_shim_default.useState(null);
    const [refreshToken, setRefreshToken] = react_shim_default.useState(0);
    const d3Ready = useD3Loader();
    const onRefresh = react_shim_default.useCallback(() => {
      postForceScan().catch(() => {
      }).finally(() => setRefreshToken((n) => n + 1));
    }, []);
    useKeyboardShortcuts({ setTab, onRefresh });
    const isSearch = tab === "search";
    const path = isSearch ? null : TAB_MAP[tab] || "/structure";
    const { data, error, loading } = usePluginFetch(path, [tab], refreshToken);
    const currentCat = CATEGORIES.find((c) => c.tabs.some((t) => t.id === tab));
    const activeLabel = currentCat ? `${currentCat.label} \u203A ${currentCat.tabs.find((t) => t.id === tab)?.label}` : tab;
    const shell = (content2) => h11(
      "div",
      { className: "codebase-viz-container" },
      h11(CategoryNav, { categories: CATEGORIES, tab, setTab, menuOpen, setMenuOpen }),
      !menuOpen && h11(
        "div",
        { className: "codebase-viz-active-label", "aria-live": "polite" },
        activeLabel
      ),
      h11("div", { className: "codebase-viz-content" }, content2),
      h11(
        "div",
        { className: "codebase-viz-shortcuts-hint", title: "Sneltoetsen" },
        "1\u20139 tabs \xB7 0 coverage \xB7 r ververs \xB7 Esc sluit inspector"
      )
    );
    if (tab === "search") {
      return shell(h11(SearchTab));
    }
    if (error) {
      return shell(
        h11(
          "div",
          { className: "codebase-viz-error" },
          h11("p", null, parseFetchError(error) || "Scan mislukt (netwerk of server)"),
          h11(
            Button,
            {
              variant: "outline",
              size: "sm",
              onClick: onRefresh
            },
            "Opnieuw proberen"
          )
        )
      );
    }
    if (loading || !data) {
      return shell(
        h11(
          "div",
          { className: "codebase-viz-loading-panel" },
          h11(ScanProgress, { active: true, tab })
        )
      );
    }
    if (tab === "sunburst" && data.tree && !data.tree.children?.length) {
      return shell(
        h11(
          "div",
          { className: "codebase-viz-empty" },
          data?.error && h11(WarningBanner, { message: data.error, onRetry: onRefresh }),
          h11(
            "p",
            null,
            data?.error ? "Scan afgebroken of geen resultaat." : "Geen bestanden gevonden in de repo."
          ),
          !data?.error && h11(
            "p",
            { className: "codebase-viz-hint" },
            "Zet CODEBASE_VIZ_REPO naar je git-root en herstart het dashboard."
          )
        )
      );
    }
    const warnMsg = data?.error || (data?.fallback ? "Gedeeltelijke data (fallback)" : null);
    let content;
    switch (tab) {
      case "sunburst":
        content = !d3Ready ? h11("p", { className: "codebase-viz-loading" }, "D3 laden...") : h11(SunburstChart, { data });
        break;
      case "force-graph":
        if (!d3Ready) {
          content = h11("p", { className: "codebase-viz-loading" }, "D3 laden...");
        } else if (!data.nodes?.length) {
          content = h11("p", { className: "codebase-viz-empty" }, "Geen Python modules gevonden.");
        } else {
          content = h11(ForceGraph, { data });
        }
        break;
      case "treemap":
        if (!d3Ready) {
          content = h11("p", { className: "codebase-viz-loading" }, "D3 laden...");
        } else if (!data.tree?.children?.length) {
          content = h11("p", { className: "codebase-viz-empty" }, "Geen bestanden voor treemap.");
        } else {
          content = h11(TreemapChart, { data });
        }
        break;
      case "metrics":
        content = h11(MetricsTab, { data });
        break;
      case "health":
        content = h11(HealthTab, { data });
        break;
      case "timeline":
        content = h11(TimelineTab, { data });
        break;
      default: {
        const spec = TABLE_TABS[tab];
        if (spec) {
          content = h11(DataTableTab, {
            data,
            title: spec.title,
            columns: spec.columns
          });
        } else {
          content = h11("p", null, "Tab nog niet ge\xEFmplementeerd.");
        }
      }
    }
    return shell(
      h11(
        "div",
        { className: "codebase-viz-tab-body" },
        warnMsg && h11(WarningBanner, { message: warnMsg, onRetry: onRefresh }),
        content
      )
    );
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
