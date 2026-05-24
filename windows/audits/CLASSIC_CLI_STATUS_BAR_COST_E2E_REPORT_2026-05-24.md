# Classic CLI Status Bar Cost E2E - PASS

**Script:** `windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1`  
**Datum:** 2026-05-24

| Stap | Status | Detail |
|------|--------|--------|
| 1/10 repo classic CLI cost artefacten | PASS | |
| 2/10 cli.py hooks + status_bar_cost.py | PASS | |
| 3/10 /cost command + merge keepOurs | PASS | |
| 4/10 UPSTREAM_SYNC classic parity | PASS | |
| 5/10 pytest status_bar_cost formatter | PASS | 12 passed |
| 6/10 pytest cli status bar + /cost | PASS | 44 passed |
| 7/10 pytest repo e2e module | PASS | 19 passed |
| 8/10 classic CLI smoke render + /cost | PASS | status_bar_cost_classic_cli_smoke.py |
| 9/10 verify_usage_cost_bar classic hooks | PASS | |
| 10/10 docs TUI + classic CLI parity | PASS | |

Alle stappen geslaagd. Handmatig: `hermes chat` (zonder `--tui`) toont kosten na model; `/cost off` verbergt kosten.

**Opnieuw draaien:**

```bat
windows\audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat
windows\audits\RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E
```
