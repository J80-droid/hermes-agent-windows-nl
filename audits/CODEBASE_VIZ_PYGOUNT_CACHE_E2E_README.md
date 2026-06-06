# Codebase Viz pygount disk-cache E2E

E2E voor pre-warm (`scripts/warm_codebase_viz_pygount_cache.py`), persistente schijfcache en launch-integratie.

**Geen** volledige `hermes-agent` pygount-scan — gebruikt een tiny temp-repo (~1 Python-bestand).

## Draaien

```cmd
audits\RUN_CODEBASE_VIZ_PYGOUNT_CACHE_E2E.bat
```

## Stappen (W1–W8)

| # | Check |
|---|--------|
| W1 | Warm script contract (`--check-only`, `--force`, seed) |
| W2 | `plugin_api`: skip `backups`/`.venv.disabled*`, atomic write, git revision |
| W3 | `launch_dashboard_on_start.ps1`: `Initialize-CodebaseVizPygountCache`, timeout 600 |
| W4 | `verify_codebase_viz_health.py` default timeout 600 |
| W5 | `_safe_repo_file_iter` skipt backups + disabled venv |
| W6 | Disk-cache write/read roundtrip |
| W7 | Warm script: check-only 2 → force 0 → check-only 0 (tiny repo) |
| W8 | pytest subset: `pygount_disk`, `warm_pygount`, `scan_skip_backups` |

## Vereisten

- `hermes-env` Python met `pygount`, `fastapi`, pytest
- Geen draaiend dashboard nodig
