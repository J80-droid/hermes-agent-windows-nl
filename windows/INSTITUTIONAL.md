# Institutionele Windows-workflow

## Principes

1. **Geen hardcoded gebruikerspaden** — conda via `HERMES_ACTIVATE_BAT` / `HERMES_CONDA_ROOT` (zie `setup_hermes_windows.ps1`, `scripts/update_knowledge.bat`).
2. **RAG-data buiten de repo** — `%USERPROFILE%\data\raw_source_files` en `lancedb\<domein>\`; centrale config `domains.yaml`; override met `HERMES_RAG_RAW_SOURCE` / `HERMES_LANCEDB_PATH`.
3. **Reproduceerbaar** — `.bat`-starters in `windows/`; logica in `.ps1`; tests onder `windows/tests/`. In `.bat` met `EnableDelayedExpansion`: **geen `\s` in paden** (bv. `windows\setup_...` wordt tab) — gebruik forward slashes (`windows/setup_...`) of variabele `SETUP_PS1`.
4. **Geen secrets in git** — `config.yaml`, logs en `.hermeslocal` staan in root `.gitignore`.
5. **Python (institutioneel)** — **conda `hermes-env`** via `Resolve-HermesPythonExe` / `HermesPythonPolicy.ps1` voor RAG, CLI, setup, ingest, **en IDE** (`.vscode/settings.json` via `sync_hermes_ide_python.ps1` / `REPAIR_PYTHON.bat`). BAT-resolver: `scripts/resolve_hermes_python.ps1`. **Native invoke:** `HermesNativeInvoke.ps1`. Repo-`.venv` niet als runtime; quarantaine via `ensure_hermes_python.ps1`. Optioneel uv alleen met `HERMES_ALLOW_UV_VENV=1`. RAG-manifest: `%LOCALAPPDATA%\Hermes\rag-deps.json` (`rag_extras_verified`). Bootstrap-state: `%LOCALAPPDATA%\hermes\launch_bootstrap.json` (schema v1, snelle start) + legacy `%LOCALAPPDATA%\hermes\launch_bootstrap.stamp`. Uitzetten fast-path: `HERMES_SKIP_LAUNCH_BOOTSTRAP_FAST_PATH=1`. Override: `HERMES_PYTHON`, `HERMES_CONDA_ROOT`. Zie `docs/HERMES_START.md`, `docs/INSTITUTIONAL_OPERATIONS.md`.
5b. **Terminal (TUI-kleuren)** — start via `launch_hermes.bat` / `start_hermes.bat` → **Windows Terminal** (`wt -M`), niet handmatig in legacy `cmd` (RGB/BGR-inversie). Standaard **één paneel** (`launcher_config.ps1`); `start_hermes_split.bat` alleen met `HERMES_START_SPLIT=1`. **UI** (banner/prompt): skin **`default`** (goud) via `APPLY_TEAM_DISPLAY.bat`. **Assistant-antwoorden:** `institutional_rich` + demo-palet via `hermes_cli/institutional_render.py` + `display_markdown.py` + `agent/rich_output.py` (niet skin-goud, niet Rich-magenta). Zie `windows/TERMINAL_WINDOWS.md`, `docs/INSTITUTIONAL_PRESENTATION.md`, porting `docs/INSTITUTIONAL_PORTING_GUIDE.md`. Override: `HERMES_SKIP_WINDOWS_TERMINAL=1`.
5c. **Hermes-home & secrets** — config **alleen** onder `%LOCALAPPDATA%\hermes\` (nooit actief `~/.hermes/config.yaml` — eenmalig `APPLY_HERMES_HOME_MIGRATION.bat` of `DEPRECATE_LEGACY_CONFIG.bat`). API-key **bron** kan `%USERPROFILE%\.hermes\.env` zijn → sync met `SYNC_HERMES_API_ENV.bat`. Drift: `VERIFY_HERMES_CONFIG_DRIFT.bat`. Runbook: `docs/HERMES_HOME_WINDOWS.md`. Bij Gemini HTTP 400 of verkeerd vault-pad: sync + doctor. Vault: `Documents\Hermes Knowledge` — zie `docs/MEMORY_ARCHITECTURE.md`. `apply_team_display.ps1` zet display op **alle** profielen; model blijft in root `config.yaml`.
6. **Eén inference-model** — `model`/`provider` alleen in `%LOCALAPPDATA%\hermes\config.yaml`; domeinprofielen (`profiles\legal`, …) alleen MCP/toolsets. Zie `docs/PROFILE_MODEL_INHERITANCE.md`.
7. **RAG-ingest performance** — preset via `HERMES_RAG_PERF_PROFILE` (`safe` / `balanced` / `fast` / `off`); defaults in `windows/scripts/rag_ingest_perf_defaults.ps1` (aangeroepen door `update_knowledge.bat`). Expliciete `HERMES_RAG_CONVERT_WORKERS`, `HERMES_RAG_EMBED_BATCH` en `HERMES_RAG_CONVERT_HEARTBEAT_SEC` winnen altijd. Ingest draait **sequentieel per bron**; `run_rag_ingest.ps1` start Python in `hermes-env` (niet een losse PowerShell zonder conda). Live voortgang: console `[LIVE]` + `%HERMES_LANCEDB_PATH%\rag_ingest_live_status.json`.

## Backup & script-keten (institutioneel)

| Onderdeel | Pad | Rol |
| --------- | --- | --- |
| Backup | `windows\backup_hermes.ps1` | **Moet in git** — `MANAGE_BACKUPS.bat`; schema **v3**; blokkeert als Hermes draait |
| Gedeelde backup-module | `windows\scripts\HermesBackupCommon.ps1` | Runtime root, robocopy-excludes, safe-for-backup gate |
| SOUL-backup | `windows\backup_soul_profiles.ps1` | `%LOCALAPPDATA%\hermes` → `localappdata_hermes/` (SOUL + `profiles/*/config.yaml`) |
| SOUL-sync | `windows\SYNC_SOUL_SNIPPETS.bat` | `SOUL_SHARED_INTERACTION.md` + `SOUL_SHARED_OUTPUT_FORMAT.md` |
| Trust runtime | `windows\SYNC_TRUST_RUNTIME.bat` | SOUL advisory + legal forensic + memory seed + limits (geen scrub); geen pause bij succes — na pull / dagelijks |
| Trust volledig | `windows\APPLY_TRUST_PROTOCOL.bat` | Bovenstaande + scrub + `RUN_TRUST_FORENSIC_E2E` — zie `docs/TRUST_FORENSIC_PROTOCOL.md` |
| Domein-toolsets | `windows\SYNC_DOMAIN_TOOLSETS.bat` | `docs/domain_toolsets.yaml` → `platform_toolsets.cli` per profiel; audit: `docs/DOMAIN_TOOLSET_AUDIT.md` |
| Presentatie | `docs/INSTITUTIONAL_PRESENTATION.md`, `docs/INSTITUTIONAL_PORTING_GUIDE.md` | Rich render + globale typografie; legacy `windows/scripts/institutional/` |
| Codebase-audit | `docs/CODEBASE_AUDIT_EVIDENCE.md` | Smoke E1/E2: `RUN_CODEBASE_SMOKE_E2E.bat`; optioneel na pull/update: `-IncludeCodebaseSmoke` / `-IncludeCodebaseSmokeE2E`; release E3: `RUN_PYTEST.bat` / `RUN_AUDITS -IncludeAllE2E` |
| Codebase Viz (dashboard) | `docs/INSTITUTIONAL_OPERATIONS.md` (sectie Codebase Viz) | `audits\verify_codebase_viz_health.py`, `audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat`; pygount timeout 240s |
| Core SOUL template | `docs/templates/SOUL_CORE_ORCHESTRATOR.md` | Routing/clarification/landkaart; niet overschreven door sync |
| Restore | `windows\restore_from_backup.ps1` | **Moet in git** — `RESTORE_FROM_BACKUP.bat`; `-RestoreRuntimeFull`, `-RestoreRuntimePersonas`, `-RestoreLegacyProfile` |
| Manifest | `windows\WindowsLocalAssetsManifest.ps1` | Enige lijst voor `_local_assets` sync/restore |
| Verify | `windows\VERIFY_WINDOWS_CHAIN.bat` | Controleert alle `.bat` → `.ps1` + kritieke bestanden |
| RAG perf | `windows\scripts\rag_ingest_perf_defaults.ps1` | **Niet** `windows\` root (sync kopieert naar `_local_assets\scripts\`) |

Na `git pull` of op een **nieuwe machine**:

1. `windows\POST_GIT_PULL.bat` (verify + trust + **SOUL anatomy deploy** `launch_soul_anatomy_deploy -Force` + domein-toolsets + taakbalk-iconen)
2. Of handmatig: `VERIFY_WINDOWS_CHAIN.bat` en `FIX_TASKBAR_ICONS.bat`
3. Bij oude clone zonder windows-bestanden: `restore_local_assets.bat`

**Taakbalk-pins (future-proof):** zie **`windows/TAAKBALK_PINS.md`**. Eénmalig vastmaken vanuit `%LOCALAPPDATA%\Hermes\taakbalk\` (`Hermes Start.lnk`, …), niet slepen uit `windows\` of `backups\`. Daarna: elke `UPDATE_HERMES.bat` en full **start** werken pins in-place bij.

**Taakbalk-iconen en lagen:**

| Onderdeel | Pad / gedrag |
| --------- | ------------- |
| Repo (dubbelklik) | `windows\*.lnk` — in git, vernieuwd bij sync |
| Persistente catalogus | `%LOCALAPPDATA%\Hermes\shortcuts\` — volledige catalogus buiten git |
| **Pin-bron taakbalk** | `%LOCALAPPDATA%\Hermes\taakbalk\` — korte namen; **hier** vastmaken |
| Bron-PNG | `assets/Hermes_logo.png` (git) of `%USERPROFILE%\.hermes\_local_assets\assets\` |
| Generator | `windows/tools/generate_colored_hermes_icons.py` → 7-lagen `.ico` (16–256 px) |
| Sync/repair | `HermesPersistentShortcuts.ps1` → `fix_hermes_taskbar_pins.ps1`; `wt.exe` + `cmd /c call` (RAG: `/k`) |
| Herstel | `FIX_TASKBAR_ICONS.bat` of `OPEN_HERMES_TAAKBALK_PINS.bat` |
| Verify | `verify_taskbar_shortcut_icons.ps1` + `verify_hermes_shortcut_paths.ps1 -IncludePinned` |
| Setup wizard | `SETUP_HERMES.bat` (standaard `--full-setup` → `OPEN_SETUP.bat`); `--files-only` zonder wizard |

Kleuren: goud = start/RAG, groen = setup, wit = update, roze = backup, cyaan = restore. Geen `hermes_taskbar_white.ico` in `.lnk`.

User-data docs (`%USERPROFILE%\data\STATUS.md`, `RECOVERY.md`) en profiel-Kanban: zie **`docs/USER_DATA_OPERATIONS.md`** (synchroon houden met repo-entrypoints).

**Backup schema v3 (backup_YYYY_MM_DD_HHMMSS):**

| Submap | Bron | Inhoud |
| ------ | ---- | ------ |
| `runtime_hermes/` | `%LOCALAPPDATA%\hermes` | Volledige runtime (config, sessions, auth, SOUL, `.env`) — **bevat secrets** |
| `legacy_hermes/` | `%USERPROFILE%\.hermes` | `_local_assets`, legacy spiegel |
| `localappdata_hermes/` | subset | SOUL, `profiles/*/config.yaml`, memories — v2 compat + snelle persona-restore |
| `repo_windows/`, `repo_assets/`, `repo_root/` | repo | Script-keten + allowlist root |
| `BACKUP_MANIFEST.json` | — | `schema_version: 3`, display-snapshot (audit) |

Hermes moet **volledig gestopt** zijn vóór backup (`Test-HermesSafeForBackup`).

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
| `backup_hermes.ps1`, `restore_from_backup.ps1`, `scripts/HermesBackupCommon.ps1` | `backups\backup_*` (snapshots, `.gitignore`) |
| Canonieke `.ico` | `*_last_run.log`, corrupt backups |
| `DELEN_MET_VRIENDEN.md`, deze gids | Runtime-fingerprints (root `.gitignore`) |

## Na clone

```cmd
cd hermes-agent\windows
SETUP_HERMES.bat
```

Daarna RAG: `windows\scripts\install_rag_extras.ps1` (pip `[rag]` + MCP), `windows\scripts\update_knowledge.bat` (index; rooktest: `scripts\rag_pipeline\ACTIVATION.md`).

**Eén checkout:** start altijd via `windows\launch_hermes.bat` in **deze** dev-repo. Diagnose: `windows\scripts\which_hermes_repo.ps1`. De map `%LOCALAPPDATA%\hermes\hermes-agent` (Nous `origin`) is een **andere** clone — niet mengen met fork/RAG zonder bewuste keuze.

**Nous-updates:** `windows\UPDATE_HERMES.bat` (of `hermes_update.bat`) → `upstream_sync.ps1 -Phase Update`: preflight, `hermes update` (upstream merge + deps), post-merge trust runtime + RAG-postinstall. Zie **[UPSTREAM_SYNC.md](UPSTREAM_SYNC.md)**. Niet `launch_hermes.bat update` alleen (geen preflight).

## P0+P1-pipeline

| Script | Doel |
| ------ | ---- |
| `windows\scripts\institutional_p0_p1.bat` | Sync MCP → `doctor --fix` → MCP-test → legal rooktest |
| `... --ingest-remaining` | Bulk ingest 7 domeinen via `run_domains_ingest.py --ingest-remaining` (**lege bronmappen worden overgeslagen**) |
| `... --kanban` | Kanban legal (niet parallel met legal-ingest) |
| `windows\VERIFY_WINDOWS_CHAIN.bat` | Backup/script-keten |

Profiel-persona: `%LOCALAPPDATA%\hermes\profiles\<naam>\SOUL.md` — zie `docs/PROFILE_SOUL.md`.

**Tests (Windows):** `pyproject.toml` gebruikt `pytest --timeout-method=thread` (geen `SIGALRM`). Enkele test: `pytest tests/hermes_cli/test_profile_orphan_wrappers.py -q` met `PYTEST_ADDOPTS=-n0`.

**Periodieke rooktest (aanbevolen):** `windows\audits\RUN_AUDITS.bat -IncludeAllE2E`. Presentatie + SOUL: `RUN_INSTITUTIONAL_E2E.bat` of `APPLY_INSTITUTIONAL_RUNTIME.bat` (incl. stap **2h** pseudo-tabel E2E).

**Pre-release (productie):**

1. `windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat`
2. `POST_GIT_PULL.bat` (of UPDATE dry-run)
3. `scripts\rag_pipeline\ACTIVATION.md` rooktest (A+B+C) op legal-profiel

Zie `docs\INSTITUTIONAL_OPERATIONS.md`.

**Legal domein:** na SOUL/taxonomie-wijziging → `RUN_LEGAL_DOMAIN_E2E.bat`; bronlayout → `windows\scripts\MIGRATE_LEGAL_LAYOUT.bat -Apply` → `update_knowledge.bat legal`. Zie `docs\LEGAL_DOMAIN_ARCHITECTURE.md`.
