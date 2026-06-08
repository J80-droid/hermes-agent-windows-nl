# NOUS drift baseline

Generated: **2026-06-08 03:36:38**
Compare: `HEAD` vs `upstream/main`

## Summary

| Metric | Count |
|--------|------:|
| All changed paths | 1277 |
| Tier A changed (must -> upstream) | 1 |
| Tier A changed (fork-intentional allowlist) | 2 |
| Tier A extra files (fork-only in Nous dirs) | 0 |
| Tier B / excluded | 1274 |
| Transitional (planned migration) | 0 |

## Tier A changed files (must -> upstream)

- `website/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-codex.md`

## Tier A changed files (fork-intentional allowlist)

- `hermes_cli/gateway_windows.py` _(fork-intentional; zie HermesNousTierPaths.ps1)_
- `pyproject.toml` _(fork-intentional; zie HermesNousTierPaths.ps1)_

## Tier A extra files (not in upstream)

_None._

## Regenerate

```powershell
powershell -NoProfile -File windows/scripts/Export-NousDriftBaseline.ps1
```

**Onderhoud (stabiel):** [NOUS_DRIFT_MAINTENANCE.md](NOUS_DRIFT_MAINTENANCE.md) - routine, scripts, taboe `SYNC_NOUS -Yes`.

**Catch-up:** `windows/SYNC_NOUS_DRIFT_CATCHUP.bat`

See [NOUS_OVERLAY_ARCHITECTURE.md](NOUS_OVERLAY_ARCHITECTURE.md).
