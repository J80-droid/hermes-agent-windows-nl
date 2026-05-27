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
  var import_react5 = __toESM(__require("react"));

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
  var import_react2 = __toESM(__require("react"));
  var h = import_react2.default.createElement;
  function ratioClass(ratio) {
    if (ratio >= 1 && ratio <= 3) return "status-ok";
    if (ratio > 3) return "status-warn";
    return "status-err";
  }
  function MetricsTab({ data }) {
    if (!data) return null;
    const { Card, CardHeader, CardTitle, CardContent } = window.__HERMES_PLUGIN_SDK__.components;
    const langs = Object.entries(data.languages || {}).sort(
      (a, b) => (b[1].code || 0) - (a[1].code || 0)
    );
    return h(
      "div",
      { className: "codebase-viz-metrics" },
      h(
        "div",
        { className: "codebase-viz-metrics-grid" },
        h(MetricCard, { label: "Total LOC", value: data.total_loc }),
        h(MetricCard, { label: "Files", value: data.total_files }),
        h(MetricCard, { label: "Languages", value: data.language_count }),
        h(MetricCard, {
          label: "Prod : Test",
          value: `${data.ratio}:1`,
          valueClass: ratioClass(data.ratio)
        })
      ),
      h(
        Card,
        null,
        h(CardHeader, null, h(CardTitle, null, "Languages")),
        h(
          CardContent,
          null,
          h(
            "table",
            { className: "codebase-viz-table" },
            h(
              "thead",
              null,
              h("tr", null, h("th", null, "Language"), h("th", null, "Files"), h("th", null, "LOC"))
            ),
            h(
              "tbody",
              null,
              ...langs.map(
                ([name, stats]) => h(
                  "tr",
                  { key: name },
                  h("td", null, name),
                  h("td", null, stats.files),
                  h("td", null, stats.code)
                )
              )
            )
          )
        )
      ),
      data.top_files?.length ? h(
        Card,
        null,
        h(CardHeader, null, h(CardTitle, null, "Top files by LOC")),
        h(
          CardContent,
          null,
          h(
            "ul",
            { className: "codebase-viz-list" },
            ...data.top_files.map(
              (f) => h("li", { key: f.path }, `${f.name} \u2014 ${f.loc} (${f.language || "?"})`)
            )
          )
        )
      ) : null
    );
  }
  function MetricCard({ label, value, valueClass }) {
    const { Card, CardContent } = window.__HERMES_PLUGIN_SDK__.components;
    return h(
      Card,
      null,
      h(
        CardContent,
        { className: "codebase-viz-metric-card" },
        h("div", { className: "codebase-viz-metric-label" }, label),
        h("div", { className: `codebase-viz-metric-value ${valueClass || ""}` }, value)
      )
    );
  }

  // src/HealthTab.jsx
  var import_react4 = __toESM(__require("react"));

  // src/usePluginFetch.js
  var import_react3 = __toESM(__require("react"));
  var API = "/api/plugins/codebase-viz";
  function usePluginFetch(path, deps = []) {
    const SDK = window.__HERMES_PLUGIN_SDK__;
    const [data, setData] = import_react3.default.useState(null);
    const [error, setError] = import_react3.default.useState(null);
    const [loading, setLoading] = import_react3.default.useState(true);
    import_react3.default.useEffect(() => {
      if (!SDK?.fetchJSON || !path) return void 0;
      const ac = new AbortController();
      setLoading(true);
      setError(null);
      SDK.fetchJSON(`${API}${path}`, { signal: ac.signal }).then(setData).catch((err) => {
        if (err?.name !== "AbortError") setError(err);
      }).finally(() => setLoading(false));
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
    const [ready, setReady] = import_react3.default.useState(!!window.d3);
    import_react3.default.useEffect(() => {
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

  // src/HealthTab.jsx
  var h2 = import_react4.default.createElement;
  function StatusBadge({ status }) {
    if (status === "error") return h2("span", { className: "status-err" }, "Error");
    if (status === "warning") return h2("span", { className: "status-warn" }, "Warning");
    return h2("span", { className: "status-ok" }, "OK");
  }
  function HealthSection({ section }) {
    const errors = section.checks.filter((c) => c.status === "error");
    const warnings = section.checks.filter((c) => c.status === "warning");
    return h2(
      "div",
      { className: "codebase-viz-health-section" },
      h2("div", { className: "codebase-viz-health-section-title" }, section.name),
      ...errors.map(
        (c) => h2(
          "div",
          { key: c.text, className: "codebase-viz-health-line" },
          h2(StatusBadge, { status: "error" }),
          " ",
          c.text
        )
      ),
      ...warnings.map(
        (c) => h2(
          "div",
          { key: c.text, className: "codebase-viz-health-line" },
          h2(StatusBadge, { status: "warning" }),
          " ",
          c.text
        )
      )
    );
  }
  function HealthTab({ data }) {
    if (!data?.sections) {
      return h2("p", null, data?.error || "Geen doctor-data.");
    }
    const { Button } = window.__HERMES_PLUGIN_SDK__.components;
    const { summary } = data;
    const score = summary?.score || 0;
    const overallClass = score >= 90 ? "status-ok" : score >= 70 ? "status-warn" : "status-err";
    return h2(
      "div",
      { className: "codebase-viz-health" },
      h2(
        "div",
        { className: "codebase-viz-health-header" },
        h2("span", { className: overallClass }, `Health: ${summary.overall}`),
        ` (${score}%) \u2014 `,
        h2("span", { className: "status-ok" }, `${summary.ok} OK`),
        " ",
        h2("span", { className: "status-warn" }, `${summary.warnings} warnings`),
        " ",
        h2("span", { className: "status-err" }, `${summary.errors} errors`),
        h2(
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
      h2(
        "div",
        { className: "codebase-viz-health-grid" },
        ...data.sections.map(
          (section) => h2(HealthSection, { key: section.name, section })
        )
      ),
      h2(
        "details",
        { style: { marginTop: "1rem" } },
        h2("summary", null, "Raw doctor output"),
        h2("pre", { className: "codebase-viz-raw" }, data.raw)
      )
    );
  }

  // src/App.jsx
  var h3 = import_react5.default.createElement;
  var CATEGORIES = [
    {
      id: "visuals",
      label: "Visuals",
      tabs: [
        { id: "sunburst", label: "Sunburst" },
        { id: "metrics", label: "Metrics" }
      ]
    },
    {
      id: "hermes",
      label: "Hermes",
      tabs: [{ id: "health", label: "Health" }]
    }
  ];
  var TAB_ENDPOINTS = {
    sunburst: "/structure",
    metrics: "/summary",
    health: "/doctor"
  };
  function CategoryNav({ categories, tab, setTab, menuOpen, setMenuOpen }) {
    return h3(
      "div",
      { className: "codebase-viz-tabs" },
      categories.map(
        (cat) => h3(
          "div",
          {
            key: cat.id,
            className: "codebase-viz-category" + (menuOpen === cat.id ? " open" : ""),
            onMouseEnter: () => setMenuOpen(cat.id),
            onMouseLeave: () => setMenuOpen(null)
          },
          h3("span", { className: "codebase-viz-category-label" }, cat.label, " \u25BE"),
          menuOpen === cat.id && h3(
            "div",
            { className: "codebase-viz-dropdown" },
            cat.tabs.map(
              (t) => h3(
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
      return h3("div", { className: "codebase-viz-error" }, "Hermes Plugin SDK niet beschikbaar.");
    }
    const { Button } = SDK.components;
    const [tab, setTab] = import_react5.default.useState("sunburst");
    const [menuOpen, setMenuOpen] = import_react5.default.useState(null);
    const d3Ready = useD3Loader();
    const path = TAB_ENDPOINTS[tab] || "/structure";
    const { data, error, loading } = usePluginFetch(path, [tab]);
    const currentCat = CATEGORIES.find((c) => c.tabs.some((t) => t.id === tab));
    const activeLabel = currentCat ? `${currentCat.label} \u203A ${currentCat.tabs.find((t) => t.id === tab)?.label}` : tab;
    const shell = (content2) => h3(
      "div",
      { className: "codebase-viz-container" },
      h3(CategoryNav, { categories: CATEGORIES, tab, setTab, menuOpen, setMenuOpen }),
      h3("div", { className: "codebase-viz-active-label" }, activeLabel),
      h3("div", { className: "codebase-viz-content" }, content2)
    );
    if (error || data?.fallback) {
      return shell(
        h3(
          "div",
          { className: "codebase-viz-error" },
          h3("p", null, parseFetchError(error) || data?.error || "Scan mislukt"),
          h3(
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
        h3(
          "p",
          { className: "codebase-viz-loading" },
          tab === "sunburst" ? "Scannen... (pygount)" : "Laden..."
        )
      );
    }
    if (tab === "sunburst" && data.tree && !data.tree.children?.length) {
      return shell(
        h3(
          "div",
          { className: "codebase-viz-empty" },
          h3("p", null, "Geen bestanden gevonden in de repo."),
          h3(
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
        if (!d3Ready) {
          content = h3("p", { className: "codebase-viz-loading" }, "D3 laden...");
        } else {
          content = h3(SunburstChart, { data });
        }
        break;
      case "metrics":
        content = h3(MetricsTab, { data });
        break;
      case "health":
        content = h3(HealthTab, { data });
        break;
      default:
        content = h3("p", null, "Tab nog niet ge\xEFmplementeerd (Sprint 2+).");
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
