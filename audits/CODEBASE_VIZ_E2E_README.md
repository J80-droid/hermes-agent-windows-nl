# Codebase Viz E2E

End-to-end audit voor het bundled dashboard-plugin **codebase-viz** (plan v2.3).

## Draaien

```bat
audits\RUN_CODEBASE_VIZ_E2E.bat
```

Of handmatig vanaf repo-root:

```bat
python audits\CodebaseVizE2E.harness.py
```

## Scenario's (V1–V11)

| Stap | Onderwerp |
|------|-----------|
| V1 | Vereiste artefacten (manifest, `plugin_api.py`, `dist/*`, tests) |
| V2 | `manifest.json` id + versie 2.3.0 |
| V3 | Pygount 3.x JSON-parser |
| V4 | Ongeldige JSON → lege rijen |
| V5 | `_path_under_root` (Windows-safe) |
| V6 | Ongeldige `CODEBASE_VIZ_REPO` |
| V7 | Health + structure via TestClient + tiny repo |
| V8 | Summary endpoint |
| V9 | `POST /force-scan` |
| V10 | WebSocket token-afwijzing |
| V11 | `pytest tests/plugins/test_codebase_viz_plugin.py` |

## Omgevingsvariabelen

| Variabele | Beschrijving |
|-----------|--------------|
| `CODEBASE_VIZ_REPO` | Te scannen repo (moet bestaan); anders bundled `.git` root |
| `CODEBASE_VIZ_TTL` | Cache-TTL seconden (default 60) |
| `CODEBASE_VIZ_DEBOUNCE` | File-watcher debounce (default 2.0) |

**Let op:** `REPO_PATH` wordt bij import vastgezet; wijzig `CODEBASE_VIZ_REPO` alleen vóór dashboard-herstart.

## Gerelateerde tests

```bat
pytest tests/plugins/test_codebase_viz_plugin.py -q
pytest tests/audits/test_codebase_viz_e2e_harness.py -q
```
