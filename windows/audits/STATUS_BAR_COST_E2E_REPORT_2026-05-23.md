# Status Bar Cost E2E (rich) - PASS

**Script:** `windows/audits/RUN_STATUS_BAR_COST_E2E.ps1`  
**Laatste run:** 2026-05-24 (10/10 PASS)  
**Hermes root:** `%LOCALAPPDATA%\hermes` (13 profielen)

| Stap | Status | Controle |
|------|--------|----------|
| 1/10 | PASS | Repo: `show_cost=true`, `cost_bar_mode=rich`, fork-modules |
| 2/10 | PASS | Institutional/diagnose drift + `merge_upstream_fork.ps1` keepOurs |
| 3/10 | PASS | Vitest: `statusBarCost`, `usageCostBar`, `createGatewayEventHandler` |
| 4/10 | PASS | Pytest: snapshot, E2E module, gateway `cost` + `cost_bar_mode` |
| 5/10 | PASS | Runtime root display |
| 6/10 | PASS | Alle profielen display |
| 7/10 | PASS | Gateway smoke: `cost_usd` + `cost_breakdown_pct` (som 100%) |
| 8/10 | PASS | `scripts/verify_usage_cost_bar.py --verify` |
| 9/10 | PASS | `windows/UPSTREAM_SYNC.md` conflict-tabel |
| 10/10 | PASS | `ui-tui/README.md` `/cost` + `cost_bar_mode` |

## Wat gedekt is

- Team-defaults: `display.show_cost: true`, `display.cost_bar_mode: rich`
- Rijke statusbalk: `$turn / $session │ cw/out/in/cr │ calls │ tools` (responsive tiers)
- Fork-owned: `hermes_cli/usage_snapshot.py`, `ui-tui/src/domain/usageCostBar.ts`
- Client-side: turn-delta (`turn_cost_usd`), tool-teller (`session_tools_executed`)
- Gateway: delegatie `_get_usage` → `build_session_usage_snapshot`; config `cost_bar_mode`
- `/usage` paneel: cost-kolommen + cost-mix
- Upstream-safe: keepOurs + dunne hooks; zie `windows/UPSTREAM_SYNC.md`

## Handmatig na deploy

```text
windows\APPLY_TEAM_DISPLAY.bat
```

Hermes herstarten of `/new`. Toggle: `/cost [on|off|toggle|status]`; legacy formaat: `config.set cost_bar_mode minimal`.

## Flags audit

```text
windows\audits\RUN_STATUS_BAR_COST_E2E.bat -ApplyDisplayFix
windows\audits\RUN_STATUS_BAR_COST_E2E.bat -SkipRuntime
windows\audits\RUN_AUDITS.bat -IncludeStatusBarCostE2E
```

**Opnieuw draaien:** `windows\audits\RUN_STATUS_BAR_COST_E2E.bat`
