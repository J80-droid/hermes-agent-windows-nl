# Classic CLI Status Bar Cost E2E - PASS

**Script:** `windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1`  
**Datum:** 2026-05-24

| Stap | Status | Detail |
|------|--------|--------|
| 1/11 repo classic CLI cost artefacten | PASS | |
| 2/11 cli.py hooks + status_bar_cost.py | PASS | |
| 3/11 /cost command + merge keepOurs | PASS | |
| 4/11 UPSTREAM_SYNC classic parity | PASS | |
| 5/11 pytest status_bar_cost formatter | PASS | |
| 6/11 pytest cli status bar + /cost | PASS | |
| 7/11 pytest repo e2e module | PASS | |
| 8/11 classic CLI smoke render + /cost | PASS | |
| 9/11 live post-turn status bar + /cost toggle | PASS | status_bar_cost_classic_cli_live_smoke.py |
| 10/11 verify_usage_cost_bar classic hooks | PASS | |
| 11/11 docs TUI + classic CLI parity | PASS | |

Alle stappen geslaagd. Live post-turn smoke dekt hermes chat statusbalk + /cost toggle (subprocess-isolatie, geen PTY).

**Opnieuw draaien:**

```bat
windows\audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat
windows\audits\RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E
```

Optioneel: `-SkipPytest` voor alleen repo/smoke/verify/docs.
