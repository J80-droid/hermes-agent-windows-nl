# Terminal CWD migration E2E

Geïsoleerde E2E voor migratie van deprecated `TERMINAL_CWD` / `MESSAGING_CWD` in profiel-`.env`
naar `terminal.cwd` in `config.yaml`. Geen mutatie van de live `%LOCALAPPDATA%\hermes` installatie.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| T1 | Repo-artefacten | `scripts/repair_terminal_cwd.py`, `windows/scripts/repair_terminal_cwd.ps1`, wiring in `repair_console_entry.ps1` |
| T2 | Geïsoleerde migratie | Actieve `TERMINAL_CWD` in temp `.env` → `terminal.cwd` + strip uit `.env` |
| T3 | Deprecatie-waarschuwing | `warn_deprecated_cwd_env_vars` stil bij expliciete `terminal.cwd` |
| T4 | Unit gate | `pytest tests/scripts/test_repair_terminal_cwd.py` |

```bat
audits\RUN_TERMINAL_CWD_MIGRATION_E2E.bat
```

Handmatige migratie (profiel `core`):

```powershell
windows\scripts\repair_terminal_cwd.ps1 -ProfileName core
```

Onderdeel van `windows\REPAIR_CONSOLE_ENTRY.bat` (stap vóór `pip install -e .`).
