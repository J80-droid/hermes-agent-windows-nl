# Hermes Windows-toolkit (institutioneel)

Nederlandstalige setup-, backup- en RAG-workflow voor deze fork. Scripts gaan uit van **conda `hermes-env`** en repo-root `hermes-agent`.

## Python (institutioneel)

| Regel | Detail |
| ----- | ------ |
| Canoniek | **conda `hermes-env`** — RAG, `launch_hermes.bat`, ingest, setup, IDE (`.vscode/settings.json`) |
| Niet gebruiken | Workspace `(venv)`; repo `.venv` als runtime (lockt bootstrap, dubbele deps) |
| Reparatie | `REPAIR_PYTHON.bat` — quarantaine `.venv`, sync IDE-interpreter, bevestig conda |
| Geavanceerd | `HERMES_ALLOW_UV_VENV=1` alleen bewust; niet productie-default |
| Future-proof | Eén waarheid: Hermes scripts + Cursor interpreter =zelfde `hermes-env` |

## Eerste installatie

| Startpunt | Script |
| --------- | ------ |
| Hoofd-setup | `SETUP_HERMES.bat` → `setup_hermes_windows.bat` (standaard **--full-setup** → `OPEN_SETUP.bat` wizard). Alleen bestanden: `--files-only` |
| Wizard | `HERMES_SETUP_WIZARD.bat` |
| One-liner (remote) | `scripts/windows/install-J..ps1` (zie `DELEN_MET_VRIENDEN.md`) |

## Dagelijks gebruik

| Taak | Script |
| ---- | ------ |
| Hermes starten | `launch_hermes.bat` / `run_hermes.ps1` (bootstrap + SOUL anatomy + institutioneel + **pending trust-nazorg** indien stamp) |
| Volledige setup | `SETUP_HERMES.bat` of `launch_hermes.bat --setup` |
| RAG-index bijwerken | `scripts/update_knowledge.bat` |
| Doctor / fixes | `DOCTOR_FIX.bat` |
| TUI-kleuren / display | `TERMINAL_WINDOWS.md`, `APPLY_TEAM_DISPLAY.bat` (skin + markdown) |
| API-keys + vault sync (split home) | `SYNC_HERMES_API_ENV.bat` — `~/.hermes/.env` → root + alle `profiles\*\`.env` (+ L4-scaffold) |
| Obsidian vault (L4) openen | `OPEN_OBSIDIAN_VAULT.bat` — sync env, scaffold, start Obsidian; zie `docs\MEMORY_ARCHITECTURE.md` |
| Profiel wisselen | `SWITCH_PROFILE.bat <naam>` of in chat `/profile use <naam>` — zie `docs\PROFILE_SWITCH.md` |
| Profiel + direct chat | `SWITCH_PROFILE_AND_CHAT.bat <naam>` (nieuwe chat = toolbox van dat profiel) |
| Toolsets per profiel | `hermes -p <naam> tools` of `SYNC_DOMAIN_TOOLSETS.bat` |
| HERMES_HOME controleren | `scripts\verify_hermes_home.ps1` |
| PowerShell lint (PSScriptAnalyzer) | `tests\RUN_PSScriptAnalyzer.bat` — 0 Warning/Error op `windows\` |
| Profielwissel E2E-audit | `audits\RUN_PROFILE_SWITCH_E2E.bat` |
| SOUL anatomy bij start (stamp) | `launch_soul_anatomy_deploy.ps1` via `launch_hermes.bat` — zie `docs\SOUL_ANATOMY_SPEC.md` |
| SOUL anatomy (handmatig + E2E) | `APPLY_SOUL_ANATOMY_RUNTIME.bat`; alleen snippets: `SYNC_SOUL_SNIPPETS.bat` |
| SOUL deploy-start E2E | `audits\RUN_SOUL_DEPLOY_START_E2E.bat` of `RUN_AUDITS.bat -IncludeSoulDeployStartE2E` |
| SOUL anatomy E2E (runtime) | `audits\RUN_SOUL_ANATOMY_E2E.ps1` |
| SOUL legacy → anatomy | `MIGRATE_SOUL_ANATOMY.bat` |
| Trust & Forensic (legal + SOUL + memory + J.) | `SYNC_TRUST_RUNTIME.bat` — volledige keten (sync, dedup, audit, production gate, /new-banner); `APPLY_TRUST_PROTOCOL.bat` (+ scrub) — `docs\TRUST_FORENSIC_PROTOCOL.md` |
| Pending trust na mislukte UPDATE | Automatisch bij `start_hermes.bat` via `scripts\launch_pending_trust_runtime.ps1` → `Invoke-TrustRuntimeLight.ps1` (geen pytest-gate); stamp `%LOCALAPPDATA%\hermes\pending_trust_runtime.json`; skip: `HERMES_SKIP_PENDING_TRUST_ON_START=1` |
| Pending trust E2E | `audits\RUN_PENDING_TRUST_START_E2E.bat` of `RUN_AUDITS.bat -IncludePendingTrustStartE2E` |
| Domein-toolsets (minimaal + opt-in) | `SYNC_DOMAIN_TOOLSETS.bat` — `docs\domain_toolsets.yaml`, `docs\DOMAIN_TOOLSET_AUDIT.md` |
| Nieuw profiel (runtime) | `set HERMES_HOME=%LOCALAPPDATA%\hermes` → `SYNC_DOMAIN_TOOLSETS.bat --create-missing` — zie `docs\DOMAIN_BLUEPRINT.md` |
| Provision E2E (smoke) | `audits\RUN_PROVISION_DOMAIN_E2E.bat` |
| Toolset E2E (13 profielen) | `audits\RUN_TOOLSET_DOMAIN_E2E.bat` of `RUN_AUDITS.bat -IncludeToolsetDomainE2E` |
| Institutionele presentatie | `docs\INSTITUTIONAL_PRESENTATION.md` |
| Core routing / landkaart | `docs\ORCHESTRATOR_ROUTING.md`, skill `landkaart` (`/landkaart`) |
| Legal lenzen (één bucket) | `docs\LEGAL_DOMAIN_ARCHITECTURE.md`, `docs\LEGAL_TAXONOMY.md`, `MIGRATE_LEGAL_LAYOUT.bat` |
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
| Backups (schema v3) | `MANAGE_BACKUPS.bat` — Hermes moet gestopt zijn; `%LOCALAPPDATA%\hermes` → `backups\backup_*` |
| Restore repo / runtime | `RESTORE_FROM_BACKUP.bat` — repo: altijd; runtime: `-RestoreRuntimeFull`; persona’s: `-RestoreRuntimePersonas`; legacy: `-RestoreLegacyProfile` |
| Backup audit (lightweight) | `audits\RUN_BACKUP_E2E.bat` |
| Statusbalk-kosten E2E (rich) | `audits\RUN_STATUS_BAR_COST_E2E.bat` · `-ApplyDisplayFix` · `RUN_AUDITS.bat -IncludeStatusBarCostE2E` |
| Klassieke CLI statusbalk-kosten E2E | `audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat` · `RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E` |
| Pareto Code router E2E | `audits\RUN_PARETO_E2E.bat` · `RUN_AUDITS.bat -IncludeParetoE2E` |
| Pseudo-tabel normalizer E2E | `audits\RUN_PSEUDO_TABLE_NORMALIZER_E2E.bat` · `RUN_AUDITS.bat -IncludePseudoTableNormalizerE2E` · `-IncludeAllE2E` |
| Platform hardening E2E (sandbox, GPU, LanceDB) | `audits\RUN_WINDOWS_PLATFORM_HARDENING_E2E.bat` · zie `docs\WINDOWS_PLATFORM_HARDENING.md` |
| Platform hardening regressie E2E | `audits\RUN_PLATFORM_HARDENING_REGRESSION_E2E.bat` |
| Codebase smoke E2E (E1/E2) | `audits\RUN_CODEBASE_SMOKE_E2E.bat` · `RUN_AUDITS.bat -IncludeCodebaseSmokeE2E` · `-IncludeAllE2E` |
| Codebase smoke (snel) | `audits\RUN_CODEBASE_SMOKE_AUDIT.bat` · `RUN_AUDITS.bat -IncludeCodebaseSmoke` |
| Na pull/update (optioneel) | `POST_GIT_PULL.bat -IncludeCodebaseSmoke` / `-IncludeCodebaseSmokeE2E` · `UPDATE_HERMES.bat` (zelfde vlaggen) |
| Memory productie-poort | `audits\RUN_MEMORY_PRODUCTION_GATE.bat` (limits + memory + trust E2E + pytest) |
| Memory-architectuur E2E | `audits\RUN_MEMORY_ARCHITECTURE_E2E.bat` (launcher → `MemoryArchitectureE2E.core.ps1`, 18/18) |
| Trust forensic E2E | `audits\RUN_TRUST_FORENSIC_E2E.bat` (launcher → `TrustForensicE2E.core.ps1`) |
| Audit PS1 syntax (IDE) | `audits\VALIDATE_AUDIT_PS1_SYNTAX.bat` |
| Taakbalk-snelkoppelingen vernieuwen | `REFRESH_TASKBAR_SHORTCUTS.bat` (`windows\*.lnk` = `cmd /c` + gekleurd `.ico`) |
| Taakbalk-icoon herstellen | `FIX_TASKBAR_ICONS.bat` |
| Nous upstream-merge (uitleg) | `UPSTREAM_SYNC.md` |
| Sentence-transformers cache warmen | `scripts/warm_sentence_transformers_cache.bat` |

## Tests

`tests/RUN_PYTEST.bat`, `tests/RUN_PSScriptAnalyzer.bat` — logs staan in `.gitignore`.

| Check | Script |
| ----- | ------ |
| `.bat` → `.ps1` ketens + pad-literals | `VERIFY_WINDOWS_CHAIN.bat` → `verify_windows_script_chain.ps1` (geen `windows\scripts` in PS1-strings; voorkomt IDE false positives) |
| SOUL sync / PS helpers | `HermesShellCommon.ps1` + `scripts/SyncSoulSnippet.psm1` — `Test-NativeCommandFailed`, IDE-safe logging; zie `docs/SOUL_ANATOMY_SPEC.md` |
| PS1-onderhoud (tags/exit) | `tools/repair_ps1_write_host_tags.py`, `tools/repair_ps1_native_exit.ps1` |

## Hermes-profielen en model

| Onderwerp | Plek |
| --------- | ---- |
| Model/provider (alle profielen) | `%LOCALAPPDATA%\hermes\config.yaml` — `hermes model` |
| Profiel legal/core (MCP) | `%LOCALAPPDATA%\hermes\profiles\<naam>\config.yaml` — **geen** `model:` |
| Opruimen oude `model:` in profielen | `DOCTOR_FIX.bat` of `hermes doctor --fix` |

Zie `docs\PROFILE_MODEL_INHERITANCE.md`.

## Configuratie

- `launcher_config.ps1` — paden en omgeving
- `team_display.defaults` — teamweergave (`skin=default`, `final_response_markdown=render`, `assistant_render_style=institutional_rich`, `assistant_palette=demo`, `assistant_label_columns=true`, `compact=false`, `streaming=false`)
- `apply_team_display.ps1` — team display naar **actief profiel** (`profiles\<active>\config.yaml`; root blijft `HERMES_HOME`)
- `audits\RUN_INSTITUTIONAL_E2E.bat` — institutioneel pakket (**11 stappen**, incl. Rich-renderer 2e); zie `audits\README.md`
- **Split-home:** `docs\HERMES_HOME_WINDOWS.md` · drift: `VERIFY_HERMES_CONFIG_DRIFT.bat` · migratie: `APPLY_HERMES_HOME_MIGRATION.bat` · E2E: `audits\RUN_HERMES_HOME_E2E.bat`, `audits\RUN_ROOT_CONFIG_INHERITANCE_E2E.bat` (`RUN_AUDITS.bat -IncludeHermesHomeE2E`)
- `sync_hermes_api_env.ps1` — API-keys + vault-paden (`OBSIDIAN_VAULT_PATH`, `WIKI_PATH`) naar alle profiel-`.env`
- `TERMINAL_WINDOWS.md` — WT, skin, markdown-kleuren, API-home
- `PSScriptAnalyzerSettings.psd1` — lint-regels

**RAG handmatig/taakbalk:** `RAG_KNOWLEDGE_UPDATE.bat` — J/N via typen + Enter, venster blijft open (`cmd /k` in `.lnk`). Regenereer via `FIX_TASKBAR_ICONS.bat` of `create_taskbar_shortcuts.ps1`. **Alleen geplande nacht-run:** `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` (`HERMES_NONINTERACTIVE=1`, geen J/N).

**Iconen (taakbalk + Verkenner):** goud = start/RAG (`hermes_logo.ico`), groen = setup (`hermes_logo_setup.ico`), wit/zilver = update (`hermes_logo_update.ico`), roze = backup, cyaan = restore. Bron: `assets/Hermes_logo.png` (of `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`). Generator bouwt **7-lagen ICO** (16–256 px). Gekleurde varianten in `windows/.gitignore` — na clone: generator + `FIX_TASKBAR_ICONS.bat`. `.lnk` in `windows\`: `cmd.exe /c` naar `.bat` (RAG: **`/k`** zodat J/N + pause zichtbaar blijven) + `IconLocation` op `.ico` (niet `.bat` slepen). Controle: `scripts/verify_taskbar_shortcut_icons.ps1`. Herstel: `python windows/tools/generate_colored_hermes_icons.py` → `FIX_TASKBAR_ICONS.bat` → **F5** in Explorer; oude taakbalk-pin opnieuw vastmaken via `.lnk`.
