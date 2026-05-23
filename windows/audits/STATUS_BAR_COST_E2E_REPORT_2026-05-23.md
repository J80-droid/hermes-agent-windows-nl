# Status Bar Cost E2E - PASS

**Script:** `windows/audits/RUN_STATUS_BAR_COST_E2E.ps1`  
**Datum:** 2026-05-23  
**Hermes root:** `%LOCALAPPDATA%\hermes` (13 profielen)

| Stap | Status | Detail |
|------|--------|--------|
| 1/8 repo defaults + artefacten | PASS | `team_display.defaults` `show_cost=true` |
| 2/8 institutional + diagnose drift guards | PASS | |
| 3/8 vitest statusBarCost | PASS | 5 tests |
| 4/8 pytest status-bar cost keten | PASS | 14 tests |
| 5/8 runtime root show_cost | PASS | |
| 6/8 runtime profielen show_cost | PASS | 13 profielen |
| 7/8 gateway _get_usage cost_usd smoke | PASS | `scripts/status_bar_cost_gateway_smoke.py` |
| 8/8 ui-tui README /cost | PASS | |

## Wat gedekt is

- Team-default `display.show_cost: true` op alle profielen (via `APPLY_TEAM_DISPLAY.bat`)
- TUI statusbalk: `formatStatusBarCost` / `mergeUsage` (geen wipe na `/usage`)
- Gateway `config.set` / `config.get` key `cost`; slash `/cost [on|off|toggle|status]`
- Drift-check in `diagnose_renderer.py` en institutioneel E2E stap 6/11

## Handmatig na deploy

```text
windows\APPLY_TEAM_DISPLAY.bat
```

Hermes herstarten of `/new` — statusbalk toont `│ ~$0.0042` na API-calls (indien prijs bekend).

## Niet in deze E2E

- Live Ink-TUI render (terminal)
- Onbekende modellen zonder prijs (`cost_usd` ontbreekt — verwacht)

**Opnieuw draaien:** `windows\audits\RUN_STATUS_BAR_COST_E2E.bat`
