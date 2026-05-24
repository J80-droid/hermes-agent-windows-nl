# Classic CLI Status Bar Cost E2E - PASS

**Script:** `windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1`  
**Datum:** 2026-05-24

| Stap | Status | Detail |
|------|--------|--------|
| 1/12 repo classic CLI cost artefacten | PASS | |
| 2/12 cli.py hooks + status_bar_cost.py | PASS | |
| 3/12 /cost command + merge keepOurs | PASS | |
| 4/12 UPSTREAM_SYNC classic parity | PASS | |
| 5/12 pytest status_bar_cost formatter | PASS | |
| 6/12 pytest cli status bar + /cost | PASS | |
| 7/12 pytest repo e2e module | PASS | |
| 8/12 classic CLI smoke render + /cost | PASS | |
| 9/12 live post-turn status bar + /cost toggle | PASS | status_bar_cost_classic_cli_live_smoke.py |
| 10/12 verify_usage_cost_bar classic hooks | PASS | |
| 11/12 docs TUI + classic CLI parity | PASS | |
| 12/12 Gemini cache pricing catalog + snapshot | PASS | usage_pricing + usage_snapshot gemini cache |

Alle stappen geslaagd. Live post-turn smoke dekt hermes chat statusbalk, /cost toggle, en gemini-3.5-flash cache-hits (geen n/a).

**Opnieuw draaien:**

```bat
windows\audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat
windows\audits\RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E
```

Optioneel: `-SkipPytest` voor alleen repo/smoke/verify/docs.
