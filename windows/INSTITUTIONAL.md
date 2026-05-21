# Institutionele Windows-workflow

## Principes

1. **Geen hardcoded gebruikerspaden** — conda via `HERMES_ACTIVATE_BAT` / `HERMES_CONDA_ROOT` (zie `setup_hermes_windows.ps1`, `scripts/update_knowledge.bat`).
2. **RAG-data buiten de repo** — `%USERPROFILE%\data\raw_source_files` en `lancedb\<domein>\`; centrale config `domains.yaml`; override met `HERMES_RAG_RAW_SOURCE` / `HERMES_LANCEDB_PATH`.
3. **Reproduceerbaar** — `.bat`-starters in `windows/`; logica in `.ps1`; tests onder `windows/tests/`. In `.bat` met `EnableDelayedExpansion`: **geen `\s` in paden** (bv. `windows\setup_...` wordt tab) — gebruik forward slashes (`windows/setup_...`) of variabele `SETUP_PS1`.
4. **Geen secrets in git** — `config.yaml`, logs en `.hermeslocal` staan in root `.gitignore`.
6. **Eén inference-model** — `model`/`provider` alleen in `%LOCALAPPDATA%\hermes\config.yaml`; domeinprofielen (`profiles\legal`, …) alleen MCP/toolsets. Zie `docs/PROFILE_MODEL_INHERITANCE.md`.
5. **RAG-ingest performance** — preset via `HERMES_RAG_PERF_PROFILE` (`safe` / `balanced` / `fast` / `off`); defaults in `windows/scripts/rag_ingest_perf_defaults.ps1` (aangeroepen door `update_knowledge.bat`). Expliciete `HERMES_RAG_CONVERT_WORKERS`, `HERMES_RAG_EMBED_BATCH` en `HERMES_RAG_CONVERT_HEARTBEAT_SEC` winnen altijd. Ingest draait **sequentieel per bron**; `run_rag_ingest.ps1` start Python in `hermes-env` (niet een losse PowerShell zonder conda). Live voortgang: console `[LIVE]` + `%HERMES_LANCEDB_PATH%\rag_ingest_live_status.json`.

## Backup & script-keten (institutioneel)

| Onderdeel | Pad | Rol |
| --------- | --- | --- |
| Backup | `windows\backup_hermes.ps1` | **Moet in git** — `MANAGE_BACKUPS.bat`, `launch_hermes.bat update` |
| Restore | `windows\restore_from_backup.ps1` | **Moet in git** — `RESTORE_FROM_BACKUP.bat` |
| Manifest | `windows\WindowsLocalAssetsManifest.ps1` | Enige lijst voor `_local_assets` sync/restore |
| Verify | `windows\VERIFY_WINDOWS_CHAIN.bat` | Controleert alle `.bat` → `.ps1` + kritieke bestanden |
| RAG perf | `windows\scripts\rag_ingest_perf_defaults.ps1` | **Niet** `windows\` root (sync kopieert naar `_local_assets\scripts\`) |

Na `git pull` of op een **nieuwe machine**:

1. `windows\POST_GIT_PULL.bat` (verify + taakbalk-iconen + icooncache)
2. Of handmatig: `VERIFY_WINDOWS_CHAIN.bat` en `FIX_TASKBAR_ICONS.bat`
3. Bij oude clone zonder windows-bestanden: `restore_local_assets.bat`

**Eenmalig** bij zwart **H** op UPDATE-pin: pin losmaken → `Hermes - update - naar taakbalk slepen.lnk` opnieuw vastmaken (niet `.bat` slepen). Daarna doet elke `UPDATE_HERMES.bat` dit automatisch.

User-data docs (`%USERPROFILE%\data\STATUS.md`, `RECOVERY.md`) en profiel-Kanban: zie **`docs/USER_DATA_OPERATIONS.md`** (synchroon houden met repo-entrypoints).

**IDE:** `.vscode/settings.json` in repo-root (PSScriptAnalyzer → `windows/PSScriptAnalyzerSettings.psd1`). Workspace-parent: `docs/IDE_VSCODE_SETTINGS.example.json`.

**Setup PS1 (single source of truth — future-proof):**

| Rol | Pad | Bewerken? |
| --- | --- | --- |
| **Canoniek** | `scripts/windows/setup_hermes_windows.ps1` | **Ja** — alle logica hier |
| **Wrapper** | `windows/setup_hermes_windows.ps1` | **Nee** — alleen doorverwijzing (`@PSBoundParameters`, max. 40 regels) |
| **Beleid** | `windows/HermesSetupScriptPolicy.ps1` | Tests + `VERIFY_WINDOWS_CHAIN` |
| **Verboden** | `Copy-Item $PSCommandPath` → `windows/` | Nooit opnieuw introduceren (dubbele IDE/lint) |

Entrypoints roepen **canoniek** aan (forward slashes in `.bat`):

- `SETUP_HERMES.bat` → `scripts/windows/setup_hermes_windows.ps1` (fallback: wrapper)
- `launch_hermes.bat` → `scripts/windows/setup_hermes_windows.ps1`
- `setup_hermes_windows.bat` (template) → zelfde canoniek PS1

Na `git pull`: `VERIFY_WINDOWS_CHAIN.bat` — faalt als iemand de wrapper per ongeluk weer volledig heeft gekopieerd (bv. oude backup-restore).

## Git vs. lokaal

| Wel in git | Niet in git |
| ---------- | ----------- |
| `.bat`, `.ps1`, `.psd1`, defaults, tests, tools | `.lnk` (taakbalk) |
| `backup_hermes.ps1`, `restore_from_backup.ps1` | `backups\backup_*` (snapshots, `.gitignore`) |
| Canonieke `.ico` | `*_last_run.log`, corrupt backups |
| `DELEN_MET_VRIENDEN.md`, deze gids | Runtime-fingerprints (root `.gitignore`) |

## Na clone

```cmd
cd hermes-agent\windows
SETUP_HERMES.bat
```

Daarna RAG: `windows\scripts\install_rag_extras.ps1` (pip `[rag]` + MCP), `windows\scripts\update_knowledge.bat` (index; rooktest: `scripts\rag_pipeline\ACTIVATION.md`).

**Eén checkout:** start altijd via `windows\launch_hermes.bat` in **deze** dev-repo. Diagnose: `windows\scripts\which_hermes_repo.ps1`. De map `%LOCALAPPDATA%\hermes\hermes-agent` (Nous `origin`) is een **andere** clone — niet mengen met fork/RAG zonder bewuste keuze.

**Nous-updates:** `windows\UPDATE_HERMES.bat` (of `hermes_update.bat`) → `upstream_sync.ps1 -Phase Update`: preflight, `hermes update` (upstream merge + deps), RAG-postinstall. Zie **[UPSTREAM_SYNC.md](UPSTREAM_SYNC.md)**. Niet `launch_hermes.bat update` alleen (geen preflight).

## P0+P1-pipeline

| Script | Doel |
| ------ | ---- |
| `windows\scripts\institutional_p0_p1.bat` | Sync MCP → `doctor --fix` → MCP-test → legal rooktest |
| `... --ingest-remaining` | Bulk ingest 7 domeinen via `run_domains_ingest.py --ingest-remaining` (**lege bronmappen worden overgeslagen**) |
| `... --kanban` | Kanban legal (niet parallel met legal-ingest) |
| `windows\VERIFY_WINDOWS_CHAIN.bat` | Backup/script-keten |

Profiel-persona: `%LOCALAPPDATA%\hermes\profiles\<naam>\SOUL.md` — zie `docs/PROFILE_SOUL.md`.

**Tests (Windows):** `pyproject.toml` gebruikt `pytest --timeout-method=thread` (geen `SIGALRM`). Enkele test: `pytest tests/hermes_cli/test_profile_orphan_wrappers.py -q` met `PYTEST_ADDOPTS=-n0`.
