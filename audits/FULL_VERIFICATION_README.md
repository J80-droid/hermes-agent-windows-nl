# Volledige verificatie (geen shortcuts)

Draait alle testlagen die standaard **niet** in `pyproject.toml` addopts zitten, plus de volledige Windows-auditketen.

## Commando

```bat
audits\RUN_FULL_VERIFICATION.bat
```

Of alleen pytest-lagen (zonder `RUN_AUDITS`):

```powershell
.\audits\RUN_FULL_VERIFICATION.ps1 -SkipRunAudits
```

## Stappen

| Stap | Wat | Log |
|------|-----|-----|
| 1 | `scripts/run_tests_parallel.py` (~29k tests, default markers) | `FULL_VERIFY_default_parallel.log` |
| 2 | `pytest -m integration` (24 tests) | `FULL_VERIFY_integration.log` |
| 3 | `pytest -m e2e` (10 harness-tests) | `FULL_VERIFY_e2e.log` |
| 4 | `pytest -m rag_integration` (LanceDB roundtrip) | `FULL_VERIFY_rag_integration.log` |
| 5 | `RUN_AUDITS.ps1 -IncludeAllE2E -IncludeInstitutionalProductionGate -IncludeRepoHygieneE2E -IncludeUpdateHermesIntegrationE2E` | `FULL_VERIFY_RUN_AUDITS.log` |

## Vereisten

- Conda env `hermes-env` met `pip install -e ".[rag]"` voor `rag_integration`
- Schone git working tree voor repo-hygiene E2E (geen untracked `.py` in root)
- Geen lopende Hermes/gateway die `agent.log` vasthoudt (Windows log rollover)

## Runtime-warnings

CLI-start filtert bekende derde-partij-ruis via `hermes_runtime_warnings.py` (discord `audioop`, PyTorch ingest). Uitzetten: `HERMES_NO_WARNING_FILTERS=1`.
