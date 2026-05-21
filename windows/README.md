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

## RAG (multi-domein)

Config: **`%USERPROFILE%\data\domains.yaml`** (voorbeeld: `docs/domains.yaml.example`).

| Commando | Betekenis |
| -------- | --------- |
| `docs\README.md` | Documentatie-index (RAG + config + profielen) |
| `docs\RAG_TWEE_FASEN.md` | Beginners: bibliotheek vs. balie, twee fasen |
| `docs\PROFILE_MODEL_INHERITANCE.md` | Model/provider centraal (niet per profiel) |
| `docs\RAG_INSTITUTIONAL_ENV.md` | Env-defaults (stale 120s, quiet torch) — institutioneel |
| `%USERPROFILE%\data\scripts\hermes.bat` | Hermes CLI zonder `conda` in PATH (`hermes-env`) |
| `scripts\update_knowledge.bat --list` | Toon alle domeinen |
| `scripts\update_knowledge.bat --mcp-test` | MCP-verify alle domeinen |
| `scripts\update_knowledge.bat` | Alle domeinen (J/N) |
| `scripts\update_knowledge.bat legal` | Alleen domein `legal` |
| `scripts\update_knowledge.bat legal --media-only` | Alleen media zonder sidecar (Whisper) |

Na elke run:

- **Eindrapport:** `%USERPROFILE%\data\lancedb\<domein>\rag_ingest_run_summary.json` + console
- **Skips:** `rag_ingest_skipped_report.md` in dezelfde map
- **Live status:** `rag_ingest_live_status.json`

Zie `../scripts/rag_pipeline/ACTIVATION.md`. `update_knowledge.bat` respecteert `HERMES_RAG_FRESH`, incrementele ingest en conda-detectie.

## Onderhoud

| Taak | Script |
| ---- | ------ |
| Backups | `MANAGE_BACKUPS.bat` |
| Lokale assets herstellen | `RESTORE_FROM_BACKUP.bat` |
| Taakbalk-snelkoppelingen vernieuwen | `REFRESH_TASKBAR_SHORTCUTS.bat` |
| Sentence-transformers cache warmen | `scripts/warm_sentence_transformers_cache.bat` |

## Tests

`tests/RUN_PYTEST.bat`, `tests/RUN_PSScriptAnalyzer.bat` — logs staan in `.gitignore`.

## Hermes-profielen en model

| Onderwerp | Plek |
| --------- | ---- |
| Model/provider (alle profielen) | `%LOCALAPPDATA%\hermes\config.yaml` — `hermes model` |
| Profiel legal/core (MCP) | `%LOCALAPPDATA%\hermes\profiles\<naam>\config.yaml` — **geen** `model:` |
| Opruimen oude `model:` in profielen | `DOCTOR_FIX.bat` of `hermes doctor --fix` |

Zie `docs\PROFILE_MODEL_INHERITANCE.md`.

## Configuratie

- `launcher_config.ps1` — paden en omgeving
- `team_display.defaults` — teamweergave (voorbeeld)
- `PSScriptAnalyzerSettings.psd1` — lint-regels

**Nacht/taakbalk:** `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` zet `HERMES_NONINTERACTIVE=1` en `HERMES_RAG_FRESH=n` (geen J/N). Regenereer `.lnk` via `create_taskbar_shortcuts.ps1`.

Iconen: `hermes_logo.ico`, `hermes_taskbar_white.ico`. Geen `.lnk` in git — gegenereerd via `create_taskbar_shortcuts.ps1`.
