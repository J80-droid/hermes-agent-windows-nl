# Codebase Viz Sprint 3 E2E (geïsoleerd)

Alleen phase-10 endpoints en `plugin_api_sprint3.py` — geen volledige plugin-suite.

## Draaien

```bat
audits\RUN_CODEBASE_VIZ_SPRINT3_E2E.bat
```

## Scenario's (S1–S9)

| Stap | Onderwerp |
|------|-----------|
| S1 | Sprint3-module callables |
| S2 | `sync_todos` vindt TODO |
| S3 | Search query &lt; 2 tekens → leeg |
| S4 | History parser: LOC per commit (niet cumulatief) |
| S5 | Dead imports — lonely module |
| S6 | Dependency cycles (a↔b) |
| S7 | API `/todos` bij `no_repo` |
| S8 | API `/search` gemockt |
| S9 | pytest subset (`-k sprint3 ...`) |

Volledige plugin-E2E: `audits/RUN_CODEBASE_VIZ_E2E.bat` (20 stappen).
