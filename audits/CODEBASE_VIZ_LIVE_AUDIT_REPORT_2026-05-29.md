# Codebase Viz Live Audit — 2026-05-29

<institutional_check>
- Controle hyperbolen: Uitgevoerd
- Controle stelligheden: Uitgevoerd
- Controle conclusies: Uitgevoerd
- Evidence-tiers: E1 (bron), E2 (pytest), E3 (live HTTP — beperkt door offline dashboard)
</institutional_check>

## Samenvatting

| Onderdeel | Status | Tier |
|-----------|--------|------|
| Plugin-artefacten + API-routes (21 endpoints + WS) | PASS | E1 |
| Frontend scripts + tab-routing | PASS | E1 |
| Dropdown/nav CSS-contract (overlap-fix) | PASS (src + dist) | E1 |
| Launch-script wiring (`launch_dashboard_on_start.ps1`) | PASS | E1 |
| pytest `test_codebase_viz_plugin.py` (81 tests) | PASS | E2 |
| Live `http://127.0.0.1:9119/codebase-viz` | **PASS** (HTTP 200, assets, health, API smoke) | E3 |
| Harness | `audits/CodebaseVizLiveE2E.harness.py` — **15/15 OK** (2026-05-29, hermes-env) | — |

**Opmerking:** `/summary` kan bij eerste scan >45s duren; harness accepteert timeout zolang `/scan-status` een actieve fase meldt (bijv. `import_edges`).

---

## Scope: scripts die op `/codebase-viz` draaien

### 1. Backend (`plugin_api.py`)

| Route | Methode | Frontend-tab / gebruik |
|-------|---------|------------------------|
| `/health` | GET | Health-tab, verify script |
| `/scan-status` | GET | `ScanProgress`, loading UI |
| `/structure` | GET | Sunburst, Treemap |
| `/dependencies` | GET | Force Graph |
| `/summary` | GET | Metrics |
| `/doctor` | GET | Health |
| `/churn` … `/history` | GET | Analysis-tabellen (Sprint 3) |
| `/search` | GET | Search-tab |
| `/force-scan` | POST | Ververs-knop, `postForceScan` |
| `/events` | WebSocket | `useFileWatcher`, `wsAuth` |

Omgevingsvariabelen: `CODEBASE_VIZ_REPO`, `CODEBASE_VIZ_TTL`, `CODEBASE_VIZ_PYGOUNT_TIMEOUT` (default 240s), `CODEBASE_VIZ_SCAN_MODE`, `CODEBASE_VIZ_MAX_MEMORY_MB`.

### 2. Frontend (gebundeld `dist/index.js`)

| Script | Rol |
|--------|-----|
| `index.jsx` | `register('codebase-viz', App)` |
| `App.jsx` | CategoryNav, tab-shell, error/loading |
| `usePluginFetch.js` | `SDK.fetchJSON` → `/api/plugins/codebase-viz/*` |
| `useScanProgress.js` | Poll `/scan-status` |
| `useKeyboardShortcuts.js` | 1–9, r, Esc |
| `useFileWatcher.js` + `wsAuth.js` | WS `/events?token=` |
| Chart/table tabs | Sunburst, ForceGraph, Treemap, Metrics, Health, DataTable, Search, Timeline |

Manifest: `entry: dist/index.js`, `css: dist/style.css`, mount `/codebase-viz`.

### 3. Launch & verify (buiten de pagina, wel in keten)

| Script | Rol |
|--------|-----|
| `windows/scripts/launch_dashboard_on_start.ps1` | `HERMES_BUNDLED_PLUGINS`, npm build, pygount pip, health |
| `audits/verify_codebase_viz_health.py` | Session token uit HTML → `/health` |
| `audits/RESTART_CODEBASE_VIZ_DASHBOARD.bat` | Herstart met timeout 240 |

---

## UI-bevinding: dropdown overlap

**Symptoom (screenshot):** Analysis-menu-items (Churn, Age Map, …) overlapten met de foutstatus (“Unauthorized”, “Opnieuw proberen”) in het midden van het paneel.

**Oorzaak (E1):**

1. Hover-only menu met `onMouseLeave` op de categorie — onbetrouwbaar boven scrollbare content.
2. Dropdown `z-index: 50` vs. dashboard main `relative z-2` — onvoldoende scheiding; geen sticky nav-shell.
3. “Unauthorized” komt van API-calls zonder geldige sessie (`usePluginFetch` → 401); los van layout, maar werd visueel bedekt door het menu.

**Fix (geïmplementeerd):**

- `CategoryNav`: klik-toggle, `aria-expanded`, Escape + outside-click sluit menu.
- CSS: `.codebase-viz-nav-shell` sticky, `z-index: 200`, `isolation: isolate`.
- Dropdown: `z-index: 1000`, ondoorzichtige achtergrond, `.codebase-viz-content { z-index: 0 }`.
- **Broodkruimel uit bij open menu:** regel `Visuals › Sunburst` (`.codebase-viz-active-label`) werd niet gerenderd terwijl dropdown open is — die tekst viel op dezelfde plek als item “Sunburst”.
- **Ruimte onder nav:** `.codebase-viz-nav-shell.is-menu-open { padding-bottom: 11rem }` zodat dropdown niet over scan-progress/content valt.
- Dist herbouwd via `npm run build`.

---

## Harness-uitvoering (2026-05-29, live)

```
audits\RUN_CODEBASE_VIZ_LIVE_E2E.bat
```

| Stap | Resultaat |
|------|-----------|
| L1 Artefacten | OK |
| L2 Manifest + routes | OK |
| L3 Frontend | OK |
| L4 CSS src/dist | OK |
| L5 Launch PS1 | OK (5/5, incl. `Update-CodebaseVizDistIfNeeded`) |
| L7 Live /codebase-viz | OK — HTTP 200 |
| L8–L10 Token + dist assets | OK |
| L11 `/health` | OK — plugin=codebase-viz, timeout 240s |
| L12 API fast | OK — `/health`, `/scan-status` |
| L13 `/summary` (heavy) | OK — timeout, scan actief (`import_edges`) |
| L14 Auth guard | OK — 401 zonder token |
| L15 pytest | OK — 81 passed |

`verify_codebase_viz_health.py`: version=2.5.0, pygount_timeout_sec=240.

---

## Aanbevelingen

1. **Dashboard starten** vóór visuele acceptatie; controleer dat `/api/plugins/codebase-viz/health` 200 geeft met session token (geen “Unauthorized” in UI).
2. **Periodiek:** `audits\RUN_CODEBASE_VIZ_LIVE_E2E.bat` na wijzigingen in `plugins/codebase-viz/`.
3. Bij 401: herlogin op dashboard of herstart via `audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat`.

---

## Gerelateerde runners

| Runner | Doel |
|--------|------|
| `RUN_CODEBASE_VIZ_LIVE_E2E.bat` | Deze audit |
| `RUN_CODEBASE_VIZ_E2E.bat` | TestClient, geen live poort |
| `RUN_CODEBASE_VIZ_PRODUCTION_E2E.bat` | 240s timeout, launch wiring |
| `verify_codebase_viz_health.py` | Snelle health na start |
