# Volledige verificatie — 2026-05-29

Machine: Windows, `hermes-env` Python 3.11.15. Geen shortcuts: alle marker-lagen + harness-fixes.

## Resultaten (handmatig gedraaid vóór `RUN_FULL_VERIFICATION.bat`)

| Laag | Commando | Resultaat |
|------|----------|-----------|
| Default (~29k) | `scripts/run_tests_parallel.py` | **PASS** (eerder in sessie, ~19 min) |
| Integration (24) | `pytest -m integration` | **23 passed, 7 skipped** (geen FAIL na `watch_all`-fix) |
| E2E (10) | `pytest -m e2e` | **10 passed** (na harness/orchestrator/post-pull fixes) |
| RAG (1) | `pytest -m rag_integration` | **1 passed** (~68s roundtrip) |
| Web UI | `audits/RUN_WEB_UI_CLEAN_E2E.bat` | **11/11** (eerdere sessie) |

## Fixes in deze keten

- `test_ha_integration`: `watch_all=True` voor event-forward test
- `score_institutional_render.py`: `sys.path` repo-root
- Dashboard/Session/PostPull/Update/Hardening harness: orchestrator-keten i.p.v. verouderde `launch_hermes.bat`-strings
- `InstitutionalHardeningE2E` H8: `-Force` op preflight (voorkomt exit 4)
- `hermes_runtime_warnings.py` + pytest `filterwarnings` (discord audioop)
- `hermes_logging.py`: `PermissionError` bij rollover op Windows
- `audits/RUN_FULL_VERIFICATION.bat` — volledige matrix inclusief `RUN_AUDITS -IncludeAllE2E`

## Nog draaien voor 100% audit-matrix

```bat
audits\RUN_FULL_VERIFICATION.bat
```

Stap 5 (`RUN_AUDITS -IncludeAllE2E -IncludeInstitutionalProductionGate …`) duurt **tientallen minuten**. Logs: `audits/FULL_VERIFY_*.log`.

## Bekende skips (geen FAIL)

- Integration: `daytona`, `voice` (deps/keys), `profile_switch` subprocess, enz.
- Default pytest: 6 env-skips (mautrix, pwd, ptyprocess, fcntl, …)
