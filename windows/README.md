# Hermes Windows-toolkit (institutioneel)

Nederlandstalige setup-, backup- en RAG-workflow voor deze fork. Scripts gaan uit van **conda `hermes-env`** en repo-root `hermes-agent`.

## Python (institutioneel)

| Regel | Detail |
| ----- | ------ |
| Canoniek | **conda `hermes-env`** — RAG, `launch_hermes.bat`, ingest, setup |
| Niet gebruiken | Workspace-map `(venv)` of kapotte `repo\.venv` zonder pip |
| Reparatie | `REPAIR_PYTHON.bat` — quarantaine kapotte `.venv`, bevestig conda |
| Geavanceerd | `HERMES_ALLOW_UV_VENV=1` alleen als `.venv` bewust gezond is (uv/pip OK) |

## Eerste installatie

| Startpunt | Script |
| --------- | ------ |
| Hoofd-setup | `SETUP_HERMES.bat` → `setup_hermes_windows.bat` (standaard **--full-setup** → `OPEN_SETUP.bat` wizard). Alleen bestanden: `--files-only` |
| Wizard | `HERMES_SETUP_WIZARD.bat` |
| One-liner (remote) | `scripts/windows/install-jamel.ps1` (zie `DELEN_MET_VRIENDEN.md`) |

## Dagelijks gebruik

| Taak | Script |
| ---- | ------ |
| Hermes starten | `launch_hermes.bat` / `run_hermes.ps1` |
| RAG-index bijwerken | `scripts/update_knowledge.bat` |
| Doctor / fixes | `DOCTOR_FIX.bat` |
| **Update fork (Nous upstream)** | `UPDATE_HERMES.bat` of `hermes_update.bat` (zelfde keten) |
| Alleen upstream-status | `powershell -File windows\upstream_sync.ps1 -Phase Preflight` |

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
| Taakbalk-snelkoppelingen vernieuwen | `REFRESH_TASKBAR_SHORTCUTS.bat` (`windows\*.lnk` = `cmd /c` + gekleurd `.ico`) |
| Taakbalk-icoon herstellen | `FIX_TASKBAR_ICONS.bat` |
| Nous upstream-merge (uitleg) | `UPSTREAM_SYNC.md` |
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

**Iconen (taakbalk + Verkenner):** goud = start/RAG (`hermes_logo.ico`), groen = setup (`hermes_logo_setup.ico`), wit/zilver = update (`hermes_logo_update.ico`), roze = backup, cyaan = restore. Bron: `assets/Hermes_logo.png` (of `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`). Generator bouwt **7-lagen ICO** (16–256 px). Gekleurde varianten in `windows/.gitignore` — na clone: generator + `FIX_TASKBAR_ICONS.bat`. `.lnk` in `windows\`: `cmd.exe /c` naar `.bat` + `IconLocation` op `.ico` (niet `.bat` slepen). Controle: `scripts/verify_taskbar_shortcut_icons.ps1`. Herstel: `python windows/tools/generate_colored_hermes_icons.py` → `FIX_TASKBAR_ICONS.bat` → **F5** in Explorer; oude taakbalk-pin opnieuw vastmaken via `.lnk`.
