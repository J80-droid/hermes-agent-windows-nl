# Codebase Viz — Full gate (Sprint 4)

Handmatige checklist na Sprint 4 hardening. Vink af tijdens rooktest op `http://127.0.0.1:9119/`.

**Vooraf:** `npm run build` in `plugins/codebase-viz/dashboard`, `pytest tests/plugins/test_codebase_viz_plugin.py -q`, dashboard herstarten.

| # | Criterium | ☐ |
|---|-----------|---|
| 1 | Tab **Codebase Viz** zichtbaar na Skills | |
| 2 | Sunburst: hover/zoom werkt | |
| 3 | Force graph: drag, zoeken, inspector, cycle edges | |
| 4 | Metrics: LOC/files/ratio + tabellen | |
| 5 | Churn: top files | |
| 6 | Age map: scatter/tabel | |
| 7 | Complexity: radon of graceful fallback | |
| 8 | TODO/FIXME tabel | |
| 9 | Blame contributors | |
| 10 | Coverage grid | |
| 11 | Health: doctor score + status classes | |
| 12 | Search: query → resultaten | |
| 13 | Dead imports tabel | |
| 14 | Config drift tabel | |
| 15 | Session stats | |
| 16 | Timeline / history chart | |
| 17 | SVG export (indien aanwezig in build) | |
| 18 | WebSocket: `.py` wijziging → graph pulse | |
| 19 | `CODEBASE_VIZ_REPO=/nonexistent` → error + retry | |
| 20 | 10 parallelle `/summary` → 1 pygount (pytest `test_thundering_herd_*`) | |
| 21 | Bundled pad `plugins/codebase-viz/dashboard/` | |
| 22 | `pytest tests/plugins/test_codebase_viz_plugin.py` groen | |
| 23 | WS met `?token=` verbindt; zonder → 4001 | |
| 24 | `/health` bevat `memory.rss_mb` / `memory.pressure` | |

## Sprint 4 extras

| Item | Verificatie |
|------|-------------|
| Sneltoetsen 1–9, 0, r, Esc | Footer-hint in plugin; Esc sluit force-graph inspector |
| Memory guard | `GET /health` → `status: degraded` bij RSS > 500 MB (met psutil) |
| Geen React require-fout | Console schoon op codebase-viz tab |
| Example 404 weg | `dashboard.hidden_plugins: [example]` indien nodig |

## Commando's

```powershell
pytest tests\plugins\test_codebase_viz_plugin.py -q
cd plugins\codebase-viz\dashboard; npm run build
pip install radon watchdog psutil
```
