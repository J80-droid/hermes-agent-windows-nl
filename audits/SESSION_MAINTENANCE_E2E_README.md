# Sessie-onderhoud (stamps) E2E

Geïsoleerde E2E voor **sessie-afhankelijk onderhoud**: stamp-helpers in `HermesShellCommon.ps1`, `HermesSessionMaintenance.ps1` (start + post-pull tail), orchestrator-wiring en POST_GIT_PULL-integratie.

**Geen** live `git pull`, geen Windows Terminal-relaunch, geen volledige RAG-ingest.

## Scenario's

| ID | Scenario | Verwachting |
|----|----------|-------------|
| S1 | Repo-artefacten | Maintenance-module, wrappers, tests, runner |
| S2 | Stamp-API in shell common | Read/Write, skip-post-pull, git head, path-watch |
| S3 | POST_GIT_PULL wiring | Conditional verify vóór trust; PostPullTail; POST_PULL_ERR |
| S4 | Start/orchestrator wiring | `launch_hermes.bat` → `launch_hermes.ps1` → orchestrator (bootstrap in orchestrator) + `-AllowFailure` dot-source |
| S5 | `start_hermes` sync cache | `Clear-HermesUpdateCheckCache` bij sync zonder relaunch |
| S6 | Launch-profielen | full autorepair + minimal start-skips |
| S7 | PowerShell parse | Maintenance + orchestrator + shell common |
| S8 | Stamp round-trip (isolated) | Write/Read + path-newer in temp `LOCALAPPDATA` |
| S9 | Skip post-pull op start | Verse `post_pull_maintenance` + zelfde `head` → skip |
| S10 | Domains fingerprint helper | null/changed/unchanged |
| S11 | PostPullTail (skips) | Domain/LanceDB/RAG uit; exit 0 |
| S12 | StartMaintenance minimal | `HERMES_MINIMAL_LAUNCH=1` → exit 0 |
| S13 | pytest subset | `tests/windows/test_hermes_session_maintenance.py` |
| S14 | Pester unit | `windows/tests/HermesSessionMaintenance.Unit.Tests.ps1` |

## Uitvoeren

```bat
audits\RUN_SESSION_MAINTENANCE_E2E.bat
```

Python harness direct:

```bat
"%USERPROFILE%\miniconda3\envs\hermes-env\python.exe" audits\SessionMaintenanceE2E.harness.py
```

Unit tests (gemockte subprocess, geen live PowerShell-keten):

```bat
pytest tests\audits\test_session_maintenance_e2e_harness.py tests\windows\test_hermes_session_maintenance.py -q -m "not e2e"
powershell -NoProfile -ExecutionPolicy Bypass -File windows\tests\HermesSessionMaintenance.Unit.Tests.ps1
```
