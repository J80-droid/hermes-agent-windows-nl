# Institutioneel hardening E2E

Geïntegreerde poort voor repo-hygiene + QuickFix + legal skills (post code-review). Geen live HTTP/API.

## Scenario's (H1–H14)

| # | Scenario |
|---|----------|
| H1 | `RepoHygieneCommon.ps1` bestaat; guard/quick_fix dot-sourcen het |
| H2 | Guard + health_check gebruiken gedeelde allowlist |
| H3 | QuickFix verplaatst ongetrackte `.py` uit root → `output/research/scripts/` |
| H4 | Na QuickFix: guard exit 0 (repo-root schoon) |
| H5 | QuickFix verplaatst ongetrackte `.xml` → `output/research/data/` |
| H6 | `health_check_repo.ps1 -Strict` exit 1 bij rommel in root |
| H7 | `upstream_sync.ps1`: guard-log + trim bij grote log |
| H8 | Guard-logbestand wordt geschreven na guard-run |
| H9 | Legal skills pytest (101 tests, gemockte HTTP) |
| H10 | `parse_uitspraak.fetch_ecli` weigert ongeldig ECLI |
| H11 | Zoekscripts: response size limit (`MAX_HTML_BYTES`) |
| H12 | `docs/WORKSPACE_CONVENTIONS.md` + `INSTITUTIONAL_OPERATIONS.md` repo-hygiene |
| H13 | `UPDATE_HERMES.bat -QuickFix` (HERMES_WIN shift-safe; alleen `-QuickFix` stopt vóór upstream) |
| H14 | Opruimen: geen test-artefacten in repo-root |

Onderdeel van `windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` (stap 4). Pytest: `tests/windows/test_repo_hygiene_institutional_e2e.py` (`-m e2e`).

## Draaien

```cmd
cd hermes-agent
audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat
```

Python: `%USERPROFILE%\miniconda3\envs\hermes-env\python.exe`
