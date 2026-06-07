# NOUS drift baseline

Generated: **2026-06-07 14:40:01**
Compare: `HEAD` vs `upstream/main`

## Summary

| Metric | Count |
|--------|------:|
| All changed paths | 1299 |
| Tier A changed (must -> upstream) | 0 |
| Tier A changed (fork-intentional allowlist) | 1 |
| Tier A extra files (fork-only in Nous dirs) | 0 |
| Tier B / excluded | 1298 |
| Transitional (planned migration) | 0 |

## Tier A changed files (must -> upstream)

_None._

## Tier A changed files (fork-intentional allowlist)

- `hermes_cli/gateway_windows.py` _(fork-intentional; zie HermesNousTierPaths.ps1)_

## Tier A extra files (not in upstream)

_None._

## Regenerate

```powershell
powershell -NoProfile -File windows/scripts/Export-NousDriftBaseline.ps1
```

See [NOUS_OVERLAY_ARCHITECTURE.md](NOUS_OVERLAY_ARCHITECTURE.md).
