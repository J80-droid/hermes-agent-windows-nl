# Dashboard on start E2E

E2E voor `windows/scripts/launch_dashboard_on_start.ps1` (Hermes dashboard op 9119 zonder browser-tab).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| D1 | Repo-artefacten | PS1 + `launch_hermes.bat` |
| D2 | Launcher wiring | Script-aanroep + skip-env + launch log |
| D3 | PS1 contract | `--no-open`, port check, status, log append |
| D4 | Documentatie | `INSTITUTIONAL_OPERATIONS` + `windows/README` |
| D5 | Skip env | `HERMES_SKIP_DASHBOARD_ON_START=1` exit 0 |
| D6 | Poort validatie | Fallback bij ongeldige poort in PS1 |
| D7 | pytest unit | `tests/windows/test_launch_dashboard_on_start.py` |

```bat
audits\RUN_DASHBOARD_ON_START_E2E.bat
```

Unit: `pytest tests/windows/test_launch_dashboard_on_start.py -q`
