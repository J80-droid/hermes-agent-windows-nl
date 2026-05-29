# Codebase Viz Live E2E

End-to-end audit voor het **live** dashboard-plugin op `http://127.0.0.1:9119/codebase-viz`, plus bron-/dist-contracten voor alle scripts die de plugin laden en voeden.

## Draaien

Dashboard moet draaien voor live HTTP-stappen (anders: SKIP op L6–L9, failures op L6):

```bat
hermes dashboard --no-open
```

Of via launch-keten:

```bat
windows\launch_hermes.bat
```

Audit:

```bat
audits\RUN_CODEBASE_VIZ_LIVE_E2E.bat
```

Optioneel:

```bat
set HERMES_DASHBOARD_BASE=http://127.0.0.1:9119
set HERMES_SKIP_PYTEST=1
```

## Scenario's (L1–L11)

| ID | Onderwerp | Verwachting |
|----|-----------|-------------|
| L1 | Artefacten | manifest, plugin_api, dist, verify, launch PS1, frontend src |
| L2 | API-routes | Alle GET/POST/WS endpoints in `plugin_api.py` |
| L3 | Frontend scripts | `usePluginFetch`, TAB_MAP, CategoryNav |
| L4 | Dropdown CSS | `codebase-viz-nav-shell` z-index 200, dropdown z-index 1000 |
| L5 | Launch wiring | bundled plugins, build, health verify, pygount timeout |
| L6 | Live `/codebase-viz` | HTTP 200 |
| L7 | Plugin assets + token | dist CSS/JS + session token |
| L8 | Live `/health` | `verify_codebase_viz_health` contract |
| L9 | API smoke (fast) | `/health`, `/scan-status` |
| L10 | API smoke (heavy) | `/summary` (timeout OK als scan actief) |
| L11 | Auth guard | Zonder token → 401/403 |
| L12 | pytest | `tests/plugins/test_codebase_viz_plugin.py` |

## Scripts in scope

| Laag | Bestand | Rol |
|------|---------|-----|
| Backend | `plugins/codebase-viz/dashboard/plugin_api.py` | FastAPI routes, cache, pygount, watchdog |
| Backend | `plugin_api_sprint3.py` | churn, search, timeline, … |
| Frontend | `src/*.jsx`, `usePluginFetch.js` | UI tabs, fetch, scan progress |
| Build | `esbuild.config.mjs` | `dist/index.js` + kopie `style.css` |
| Launch | `windows/scripts/launch_dashboard_on_start.ps1` | bundled plugin, `Update-CodebaseVizDistIfNeeded`, health |
| Verify | `audits/verify_codebase_viz_health.py` | post-start health check |

## UI-fix dropdown overlap

Categorie-menu's gebruiken klik-toggle + sticky `codebase-viz-nav-shell` (z-index 200) zodat dropdowns (z-index 1000) boven scrollbare content en het dashboard `z-2` main-paneel blijven.

Na wijzigingen in `src/`:

```bat
cd plugins\codebase-viz\dashboard
npm run build
```

## Gerelateerd

- `audits/CODEBASE_VIZ_E2E_README.md` — geïsoleerde TestClient E2E (geen live poort)
- `audits/CODEBASE_VIZ_LIVE_AUDIT_REPORT_2026-05-29.md` — uitvoeringsrapport
