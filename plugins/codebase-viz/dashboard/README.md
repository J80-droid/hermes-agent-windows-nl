# Codebase Viz (dashboard plugin)

Bundled Hermes-dashboardtab voor repo-structuur, LOC-metrics, import-afhankelijkheden en `hermes doctor`.

- **Plan:** `docs/plans/2026-05-27-codebase-viz-dashboard-plugin.md` (v2.5.0)
- **Versie:** `2.5.0` (manifest + `/health`)
- **API-prefix:** `/api/plugins/codebase-viz/`
- **Frontend:** React via `window.__HERMES_PLUGIN_SDK__` (`fetchJSON`, geen `useApi`)

## Bouwen

```bash
cd plugins/codebase-viz/dashboard
npm install
npm run build
```

Artefacten in `dist/`: `index.js`, `style.css`, `d3.v7.min.js`.

React komt uit `window.__HERMES_PLUGIN_SDK__` via `src/react-shim.js` (esbuild alias) — **niet** `external: ['react']` met `require()` in de browser.

Optionele Python-tools (in dezelfde venv als Hermes):

```bash
pip install watchdog radon psutil
```

## Configuratie

| Env | Default | Beschrijving |
|-----|---------|--------------|
| `CODEBASE_VIZ_REPO` | bundled `hermes-agent` root (`.git`) | Scan-doel |
| `CODEBASE_VIZ_TTL` | `60` | Response-cache (s) |
| `CODEBASE_VIZ_DEBOUNCE` | `2.0` | Watcher batch-interval |
| `CODEBASE_VIZ_PYGOUNT_TIMEOUT` | `30` | `pygount` subprocess timeout |
| `CODEBASE_VIZ_MAX_MEMORY_MB` | `500` | RSS-drempel; boven limiet → stale cache of `memory_pressure` |

`REPO_PATH` wordt bij module-import bepaald; na env-wijziging dashboard herstarten.

## Endpoints

| Methode | Pad | Beschrijving |
|---------|-----|--------------|
| GET | `/health` | Status, repo, watcher, `memory` (RSS / pressure) |
| GET | `/structure` | Directory tree + LOC summary |
| GET | `/dependencies` | Import-graaf (nodes/edges) |
| GET | `/summary` | Aggregaten + top files/modules |
| GET | `/doctor` | `hermes doctor` parse (graceful bij ontbrekende CLI) |
| POST | `/force-scan` | Cache legen + pygount refresh |
| WS | `/events?token=` | File-change events (watchdog optioneel) |

Bij `no_repo` of compute-fouten: HTTP 200 met `error` / `fallback: true` en lege structuren.

Pygount timeouts worden als `RuntimeError` / `fallback` afgehandeld (geen 500).

## Tests

```bash
pytest tests/plugins/test_codebase_viz_plugin.py -q
audits/RUN_CODEBASE_VIZ_E2E.bat
audits/RUN_CODEBASE_VIZ_SPRINT4_E2E.bat
```

Unit tests mocken `subprocess`, `asyncio.create_subprocess_exec` en pygount-fouten; geen live dashboard-browser in pytest.

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
9. **API (optioneel):** `GET /api/plugins/codebase-viz/health` → `repo_path`, `version` `2.5.0`, `memory`.

Bij problemen: `pip install watchdog radon`; `pygount` op PATH; dashboard **herstarten** na env-wijziging.

**Console: `example/dist/index.js` 404** — herstart dashboard na `git pull`; bundled `plugins/example-dashboard/dashboard/dist/index.js` hoort aanwezig te zijn. Optioneel tab verbergen:

```yaml
dashboard:
  hidden_plugins:
    - example
```

## Sprint 4 — Hardening (v2.5.0)

| Feature | Details |
|---------|---------|
| Thundering herd | `asyncio.Lock` + pytest parallel cache miss |
| Memory guard | `CODEBASE_VIZ_MAX_MEMORY_MB` (default 500), `pip install psutil` |
| Shortcuts | `1`–`9` tabs, `0` coverage, `r` force-scan+refresh, `Esc` inspector |
| Checklist | `docs/checklists/codebase-viz-sprint4-full-gate.md` |

## Sprint 3 — Analysis & tools (v2.4.0)

| Tab | Endpoint |
|-----|----------|
| Churn | `GET /churn` |
| Age Map | `GET /age-map` |
| Complexity | `GET /complexity` (radon) |
| TODO/FIXME | `GET /todos` |
| Blame | `GET /blame` |
| Coverage | `GET /coverage` |
| Dead Imports | `GET /dead-imports` |
| Config Drift | `GET /config-drift` |
| Session Stats | `GET /session-stats` |
| Search | `GET /search?q=` |
| Timeline | `GET /timeline` |
| Metrics history chart | `GET /history` |

Backend: `plugin_api_sprint3.py` · Frontend: `DataTableTab`, `SearchTab`, `TimelineTab`, `HistoryChart`.

Sprint 3 E2E (alleen phase-10): `audits/RUN_CODEBASE_VIZ_SPRINT3_E2E.bat`

| Env | Default | Beschrijving |
|-----|---------|--------------|
| `CODEBASE_VIZ_GIT_TIMEOUT` | `15` | Git subprocess timeout (s) |
| `CODEBASE_VIZ_MAX_TODO_FILES` | `8000` | Max bestanden voor TODO-scan |

## Sprint 2 — Core viz (geleverd)

- **Force Graph** — `/dependencies`, drag/zoom, zoekfilter, inspector (in/out imports), Live-badge via WebSocket
- **Treemap** — `/structure`, drill-down per directory (klik map-cel of breadcrumb)
- **Auth** — `src/wsAuth.js`: `window.__HERMES_SESSION_TOKEN__` (kanban-patroon) + cookie-fallback

## MVP scope (Sprint 1)

- Sunburst, Metrics, Health tabs
