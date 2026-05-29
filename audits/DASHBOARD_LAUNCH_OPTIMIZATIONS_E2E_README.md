# Dashboard launch optimizations E2E

Valideert de start-optimalisaties voor stap 8 (web dashboard):

| Onderdeel | Wat wordt gecontroleerd |
|-----------|-------------------------|
| `web-dashboard-deps.json` | `Test-HermesNeedsWebDashboardPipInstall` fast-path |
| Pygount-cache | Mismatch-detectie, `FIX_CODEBASE_VIZ_CACHE.bat`, repair-script |
| Launch PS1 | Conditionele pip, skip dashboard-restart, auto-heal cache |
| Tests | `tests/plugins/conftest.py` + unit gate |

## Draaien

```bat
audits\RUN_DASHBOARD_LAUNCH_OPTIMIZATIONS_E2E.bat
```

## Gerelateerd

- `windows\FIX_CODEBASE_VIZ_CACHE.bat` — handmatige pygount-cache repair
- `audits\RUN_CODEBASE_VIZ_PYGOUNT_CACHE_E2E.bat` — pygount disk-cache E2E
- `windows\tests\HermesWebDashboardLaunch.Unit.Tests.ps1` — PowerShell unit tests
