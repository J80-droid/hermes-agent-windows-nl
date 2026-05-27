# Codebase Viz (dashboard plugin)

Bundled Hermes-dashboardtab voor repo-structuur, LOC-metrics, import-afhankelijkheden en `hermes doctor`.

- **Plan:** `docs/plans/2026-05-27-codebase-viz-dashboard-plugin.md` (v2.3)
- **API-prefix:** `/api/plugins/codebase-viz/`
- **Frontend:** React via `window.__HERMES_PLUGIN_SDK__` (`fetchJSON`, geen `useApi`)

## Bouwen

```bash
cd plugins/codebase-viz/dashboard
npm install
npm run build
```

Artefacten in `dist/`: `index.js`, `style.css`, `d3.v7.min.js`.

## Configuratie

| Env | Default | Beschrijving |
|-----|---------|--------------|
| `CODEBASE_VIZ_REPO` | bundled `hermes-agent` root (`.git`) | Scan-doel |
| `CODEBASE_VIZ_TTL` | `60` | Response-cache (s) |
| `CODEBASE_VIZ_DEBOUNCE` | `2.0` | Watcher batch-interval |
| `CODEBASE_VIZ_PYGOUNT_TIMEOUT` | `30` | `pygount` subprocess timeout |

`REPO_PATH` wordt bij module-import bepaald; na env-wijziging dashboard herstarten.

## Endpoints

| Methode | Pad | Beschrijving |
|---------|-----|--------------|
| GET | `/health` | Status, repo, watcher |
| GET | `/structure` | Directory tree + LOC summary |
| GET | `/dependencies` | Import-graaf (nodes/edges) |
| GET | `/summary` | Aggregaten + top files/modules |
| GET | `/doctor` | `hermes doctor` parse (graceful bij ontbrekende CLI) |
| POST | `/force-scan` | Cache legen + pygount refresh |
| WS | `/events?token=` | File-change events (watchdog optioneel) |

Bij `no_repo` of compute-fouten: HTTP 200 met `error` / `fallback: true` en lege structuren.

## Tests

```bash
pytest tests/plugins/test_codebase_viz_plugin.py -q
audits/RUN_CODEBASE_VIZ_E2E.bat
```

## Rooktest (dashboard)

1. **Optioneel env** (PowerShell, vóór dashboard-start):
   ```powershell
   $env:CODEBASE_VIZ_REPO = "D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
   ```
2. **Hermes dashboard** herstarten (of browser hard refresh op `http://127.0.0.1:9119/`).
3. Tab **Codebase Viz** (na Skills) — laadt zonder rode SDK-fout.
4. **Sunburst:** diagram met gekleurde segmenten; klik zoomt; geen lege staat tenzij geen repo.
5. **Metrics:** LOC/files/talen; top files/modules.
6. **Health:** score + secties met groen/geel/rood labels (geen emoji).
7. **Force Scan** (indien knop): geen crash; data ververst.
8. **D3:** DevTools → Network → `d3.v7.min.js` → status 200.
9. **API (optioneel):** `GET /api/plugins/codebase-viz/health` → `repo_path`, `version` `2.3.0`.

Bij problemen: `pip install watchdog` (live watcher); `pygount` op PATH; dashboard **herstarten** na env-wijziging.

## Sprint 2 — Core viz (geleverd)

- **Force Graph** — `/dependencies`, drag/zoom, zoekfilter, inspector (in/out imports), Live-badge via WebSocket
- **Treemap** — `/structure`, drill-down per directory (klik map-cel of breadcrumb)
- **Auth** — `src/wsAuth.js`: `window.__HERMES_SESSION_TOKEN__` (kanban-patroon) + cookie-fallback

## MVP scope (Sprint 1)

- Sunburst, Metrics, Health tabs
