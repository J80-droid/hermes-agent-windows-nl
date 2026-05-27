# Codebase Viz — Sprint 4 E2E

Hardening: memory guard, thundering herd, keyboard shortcuts bundle, example-plugin dist.

## Run

```bat
audits\RUN_CODEBASE_VIZ_SPRINT4_E2E.bat
```

```powershell
python audits/CodebaseVizSprint4E2E.harness.py
```

## Steps (H1–H9)

| Step | Check |
|------|--------|
| H1 | manifest `2.5.0` |
| H2 | `useKeyboardShortcuts.js`, `react-shim.js` |
| H3 | dist markers + geen `require("react")` |
| H4 | `/health` → `memory`, `version` |
| H5 | 10× parallel summary → 1 pygount |
| H6 | stale cache bij memory pressure |
| H7 | memory_pressure zonder cache |
| H8 | example `dist/index.js` |
| H9 | full-gate checklist doc |

Unit tests: `pytest tests/plugins/test_codebase_viz_plugin.py -q`
