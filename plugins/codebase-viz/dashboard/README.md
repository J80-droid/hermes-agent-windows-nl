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
pip install pygount watchdog radon psutil
```

`pygount` zit niet in `[web]`; `launch_dashboard_on_start.ps1` installeert het automatisch bij workspace-plugins.

## Configuratie

| Env | Default | Beschrijving |
|-----|---------|--------------|
| `CODEBASE_VIZ_REPO` | bundled `hermes-agent` root (`.git`) | Scan-doel |
| `CODEBASE_VIZ_TTL` | `60` | Response-cache (s) |
| `CODEBASE_VIZ_DEBOUNCE` | `2.0` | Watcher batch-interval |
| `CODEBASE_VIZ_PYGOUNT_TIMEOUT` | `240` | `pygount` subprocess timeout (volledige fork-repo); ongeldige waarde → fallback 240 |
| `CODEBASE_VIZ_SCAN_MODE` | `incremental` | Productiepad: `incremental` (SWR + delta-refresh) of `full` |
| `CODEBASE_VIZ_MAX_MEMORY_MB` | `500` | RSS-drempel; boven limiet → stale cache of `memory_pressure` |

`REPO_PATH` wordt bij module-import bepaald; na env-wijziging dashboard herstarten.

### Scan-snelheid & cache

| Situatie | Verwachting |
|----------|-------------|
| **Eerste load** (Sunburst) | Volledige `hermes-agent` root: tot **~240 s** (één `pygount`-run); kleine repo's vaak sneller |
| **Herladen binnen TTL** | **< 1 s** — resultaat uit server-cache (`CODEBASE_VIZ_TTL`, default **60 s**) |
| **Tab wisselen** (Metrics, Treemap) | Vaak snel: deelt dezelfde `pygount`-cache |
| **Force Scan / `r`** | Cache geleegd → opnieuw volledige scan |

**Gedeelde telemetry (server-cache):**

| Sleutel | Gebruikt door |
|---------|----------------|
| `pygount` | Sunburst, Treemap, Metrics (LOC) |
| `import_edges` | Force Graph, Metrics, Dependencies, Dead Imports |
| `structure` / `summary` / `dependencies` | Per-tab endpoint (bouwen op bovenstaande) |
| `churn`, `todos`, `blame`, … | Aparte git/radon-scans (eigen TTL, niet pygount) |

Voortgang in de UI: `GET /scan-status` (phase, `repo_label`, elapsed/max timeout, pseudo-progress, `scan_mode`, `refresh`) + progress bar. Tijdens laden zie je subtiel **Scan: …/hermes-agent** (live fase-wissel).

In `incremental` mode zijn `/structure`, `/summary` en `/dependencies` **stale-while-revalidate**:
- direct gecachte response (`served_from_cache`)
- daarna background refresh (`refresh_in_background`)
- response metadata: `last_updated_at`, `stale_age_sec`, `scan_mode`

Lang scannen is dus **normaal** bij de eerste request na start of na `force-scan`. Daarna is het gecached.

Sneller op grote repos (PowerShell, vóór dashboard-start):

```powershell
$env:CODEBASE_VIZ_TTL = "300"
$env:CODEBASE_VIZ_PYGOUNT_TIMEOUT = "300"   # als 240s nog te krap
$env:CODEBASE_VIZ_REPO = "D:\pad\naar\kleinere-repo"   # optioneel: alleen submap
```

Controle: `GET /api/plugins/codebase-viz/health` → `pygount_cached: true` na eerste succesvolle scan.

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
# Altijd vanaf hermes-agent repo-root, met Hermes-venv (fastapi in .[web]):
cd path/to/hermes-agent
pip install -e ".[web]"
pytest tests/plugins/test_codebase_viz_plugin.py -q -o "addopts="
```

Windows (aanbevolen):

```bat
audits\RUN_CODEBASE_VIZ_UNIT_TESTS.bat
audits\RUN_CODEBASE_VIZ_E2E.bat
audits\RUN_CODEBASE_VIZ_SPRINT4_E2E.bat
audits\RUN_CODEBASE_VIZ_LAUNCH_E2E.bat
```

Niet vanuit `plugins/codebase-viz/dashboard` draaien — dan ontbreekt vaak `fastapi` en collection faalt.

### App starten (aanbevolen)

Gebruik het normale Windows-startscript — die regelt automatisch workspace-plugins, `pip install -e .[web]` en opent de browser op Codebase Viz:

```bat
start_hermes.bat
```

Alleen dashboard (geen TUI):

```bat
audits\RUN_DASHBOARD_WS_DEV.bat
```

`launch_dashboard_on_start.ps1` zet bij een workspace met `plugins/codebase-viz`:

- `HERMES_BUNDLED_PLUGINS` → `<repo>\plugins`
- `pip install -e .[web]` (fastapi/uvicorn in conda `hermes-env`)
- oude user-plugins `%LOCALAPPDATA%\hermes\plugins\codebase-viz` → `.bak`
- geen automatische browser-tab bij `start_hermes.bat` (optioneel: `HERMES_DASHBOARD_OPEN_PATH=/codebase-viz`)

Controle in browser → Network → `GET /api/plugins/codebase-viz/health`:

- `version`: `2.5.0`
- `pygount_timeout_sec`: **240** (niet 30)
- `plugin_api_path`: pad onder deze repo

Zie je nog **30 seconds** in de fouttekst? Er draait dan een **oud dashboard-proces**. Oplossing: `audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat` of Hermes volledig afsluiten en opnieuw `start_hermes.bat`.

### Scan-voortgang (UI)

- Eén progress bar tijdens laden (geen dubbele `<progress>` + custom bar).
- Oude backend zonder `pygount_timeout_sec`: gele hint + lokale timer (geen `/scan-status` spam).
- Nieuwe backend: polling `GET /scan-status` + server elapsed/progress + scan-doel (`repo_label`).

Console (filter `[codebase-viz]`): `scan gestart`, `fetch start/ok`; bij oude API één regel `voortgang via lokale timer`.

Unit tests mocken `subprocess` en gebruiken een **kleine temp-repo** — die slagen ook als pygount op de echte `hermes-agent` root **>240s** nodig heeft.

### UI-navigatie (categorie-dropdowns)

- Klik op **Visuals / Analysis / Hermes / Tools** (niet alleen hover).
- Broodkruimel (`Visuals › Sunburst`) wordt **verborgen** zolang een menu open is (voorkomt overlap met dropdown-items).
- Sticky nav + `padding` onder open menu; Force Graph: `graph.capped` (geen `capped is not defined`).

### Live E2E-audit (9119)

```bat
audits\RUN_CODEBASE_VIZ_LIVE_E2E.bat
```

Zie `audits/CODEBASE_VIZ_LIVE_E2E_README.md` en rapport `audits/CODEBASE_VIZ_LIVE_AUDIT_REPORT_2026-05-29.md`. Dashboard moet draaien voor HTTP-stappen L7+.

**Loopback:** `GET /api/auth/me` → 401 is normaal (geen OAuth); dashboard slaat die call sinds web-fix over op localhost.

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
