# Hermes Windows-toolkit (institutioneel)

Nederlandstalige setup-, backup- en RAG-workflow voor deze fork. Scripts gaan uit van **conda `hermes-env`** en repo-root `hermes-agent`.

## Eerste installatie

| Startpunt | Script |
| --------- | ------ |
| Hoofd-setup | `SETUP_HERMES.bat` → `setup_hermes_windows.ps1` |
| Wizard | `HERMES_SETUP_WIZARD.bat` |
| One-liner (remote) | `scripts/windows/install-jamel.ps1` (zie `DELEN_MET_VRIENDEN.md`) |

## Dagelijks gebruik

| Taak | Script |
| ---- | ------ |
| Hermes starten | `launch_hermes.bat` / `run_hermes.ps1` |
| RAG-index bijwerken | `scripts/update_knowledge.bat` |
| Doctor / fixes | `DOCTOR_FIX.bat` |
| Update fork | `UPDATE_HERMES.bat` / `hermes update` |

## Onderhoud

| Taak | Script |
| ---- | ------ |
| Backups | `MANAGE_BACKUPS.bat` |
| Lokale assets herstellen | `RESTORE_FROM_BACKUP.bat` |
| Taakbalk-snelkoppelingen vernieuwen | `REFRESH_TASKBAR_SHORTCUTS.bat` |
| Sentence-transformers cache warmen | `scripts/warm_sentence_transformers_cache.bat` |

## RAG

Zie `../scripts/rag_pipeline/ACTIVATION.md`. `update_knowledge.bat` respecteert `HERMES_RAG_FRESH`, `HERMES_RAG_INCREMENTAL` en conda-detectie.

## Tests

`tests/RUN_PYTEST.bat`, `tests/RUN_PSScriptAnalyzer.bat` — logs staan in `.gitignore`.

## Configuratie

- `launcher_config.ps1` — paden en omgeving
- `team_display.defaults` — teamweergave (voorbeeld)
- `PSScriptAnalyzerSettings.psd1` — lint-regels

Iconen: `hermes_logo.ico`, `hermes_taskbar_white.ico`. Geen `.lnk` in git — gegenereerd via `create_taskbar_shortcuts.ps1`.
