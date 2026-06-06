# Pytest audit-env E2E

Geïsoleerde poort voor **institutional production gate pytest-wiring** (2026-06):

- Geen `-p pytest_timeout` in default `PYTEST_ADDOPTS` (`HermesShellCommon.ps1`)
- `Clear-HermesPytestAddoptsForAudit` + `Get-HermesAuditPytestOverrideArgs` in audit E2E-scripts
- `RUN_INSTITUTIONAL_PRODUCTION_GATE` wist `PYTEST_ADDOPTS` vóór subprocessen
- RAG `sync_profile_mcp_from_domains.py` bootstrap voor `profile_mcp_format`
- `institutional_p0_p1.bat` gebruikt `%HERMES_REPO%\windows\scripts\update_knowledge.bat`

## Draaien

```cmd
audits\RUN_PYTEST_AUDIT_ENV_E2E.bat
```

## Stappen (E1–E8)

| Stap | Check |
|------|--------|
| E1 | `HermesShellCommon` helpers + geen `-p pytest_timeout` in default |
| E2 | Regressie: dubbele plugin met `-p pytest_timeout` faalt collect |
| E3 | Gewiste env + audit override → pytest collect OK |
| E4 | `sync_profile_mcp_from_domains.py --check` zonder importfout |
| E5 | `institutional_p0_p1.bat` pad + bestand bestaat |
| E6 | Production gate roept `Clear-HermesPytestAddoptsForAudit` aan |
| E7 | Python/KR institutional E2E cores gebruiken helpers |
| E8 | Hardening H9 wist `PYTEST_ADDOPTS` |

## Unit tests (gemockt)

```cmd
pytest tests/audits/test_pytest_audit_env_e2e_harness.py tests/scripts/test_sync_profile_mcp_bootstrap.py -q
```
