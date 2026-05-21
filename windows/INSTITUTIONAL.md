# Institutionele Windows-workflow

## Principes

1. **Geen hardcoded gebruikerspaden** — conda via `HERMES_ACTIVATE_BAT` / `HERMES_CONDA_ROOT` (zie `setup_hermes_windows.ps1`, `scripts/update_knowledge.bat`).
2. **RAG-data buiten de repo** — `%USERPROFILE%\data\raw_source_files` en `lancedb\<domein>\`; centrale config `domains.yaml`; override met `HERMES_RAG_RAW_SOURCE` / `HERMES_LANCEDB_PATH`.
3. **Reproduceerbaar** — `.bat`-starters in `windows/`; logica in `.ps1`; tests onder `windows/tests/`.
4. **Geen secrets in git** — `config.yaml`, logs en `.hermeslocal` staan in root `.gitignore`.
6. **Eén inference-model** — `model`/`provider` alleen in `%LOCALAPPDATA%\hermes\config.yaml`; domeinprofielen (`profiles\legal`, …) alleen MCP/toolsets. Zie `docs/PROFILE_MODEL_INHERITANCE.md`.
5. **RAG-ingest performance** — preset via `HERMES_RAG_PERF_PROFILE` (`safe` / `balanced` / `fast` / `off`); defaults in `windows/scripts/rag_ingest_perf_defaults.ps1` (aangeroepen door `update_knowledge.bat`). Expliciete `HERMES_RAG_CONVERT_WORKERS`, `HERMES_RAG_EMBED_BATCH` en `HERMES_RAG_CONVERT_HEARTBEAT_SEC` winnen altijd. Ingest draait **sequentieel per bron**; `run_rag_ingest.ps1` start Python in `hermes-env` (niet een losse PowerShell zonder conda). Live voortgang: console `[LIVE]` + `%HERMES_LANCEDB_PATH%\rag_ingest_live_status.json`.

## Git vs. lokaal

| Wel in git | Niet in git |
| ---------- | ----------- |
| `.bat`, `.ps1`, `.psd1`, defaults, tests, tools | `.lnk` (taakbalk) |
| Canonieke `.ico` | `*_last_run.log`, corrupt backups |
| `DELEN_MET_VRIENDEN.md`, deze gids | Runtime-fingerprints (root `.gitignore`) |

## Na clone

```cmd
cd hermes-agent\windows
SETUP_HERMES.bat
```

Daarna RAG: `windows\scripts\install_rag_extras.ps1` (pip `[rag]` + MCP), `windows\scripts\update_knowledge.bat` (index; rooktest: `scripts\rag_pipeline\ACTIVATION.md`).

**Eén checkout:** start altijd via `windows\launch_hermes.bat` in **deze** dev-repo. Diagnose: `windows\scripts\which_hermes_repo.ps1`. De map `%LOCALAPPDATA%\hermes\hermes-agent` (Nous `origin`) is een **andere** clone — niet mengen met fork/RAG zonder bewuste keuze.

**Nous-updates:** `windows\hermes_update.bat` zet `HERMES_UPDATE_FROM_UPSTREAM=1` → merge **NousResearch `upstream/main`**, daarna deps. Zie **[UPSTREAM_SYNC.md](UPSTREAM_SYNC.md)**.
