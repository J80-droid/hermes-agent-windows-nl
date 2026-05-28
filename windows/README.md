# Hermes Windows-toolkit (institutioneel)

Nederlandstalige setup-, backup- en RAG-workflow voor deze fork. Scripts gaan uit van **conda `hermes-env`** en repo-root `hermes-agent`.

**Handige commando's (fork, cheat sheet):** [`docs/INSTITUTIONAL_OPERATIONS.md`](../docs/INSTITUTIONAL_OPERATIONS.md#handige-commandos-fork) — dagelijks, repo-hygiene, upstream, RAG, audits, pytest. Onderstaande tabellen zijn per domein; dupliceer geen losse `.bat`-lijsten elders zonder link naar die sectie.

## Python (institutioneel)

| Regel | Detail |
| ----- | ------ |
| Canoniek | **conda `hermes-env`** — RAG, `launch_hermes.bat`, ingest, setup, IDE (`.vscode/settings.json`) |
| Niet gebruiken | Workspace `(venv)`; repo `.venv` als runtime (lockt bootstrap, dubbele deps) |
| Reparatie | `REPAIR_PYTHON.bat` — quarantaine `.venv`, sync IDE-interpreter, bevestig conda, RAG-check (non-interactive in CI) |
| Parent workspace IDE (PSES) | `APPLY_WORKSPACE_IDE_SETTINGS.bat` — schrijft `Hermes_agent_WS\.vscode\settings.json`; daarna Reload Window + Restart Session — `docs\WORKSPACE_IDE_SETUP.md` |
| Geavanceerd | `HERMES_ALLOW_UV_VENV=1` alleen bewust; niet productie-default |
| Override | `HERMES_PYTHON`, `HERMES_CONDA_ROOT`, `HERMES_CONDA_ENV` — zie `HermesPythonPolicy.ps1` |
| RAG-manifest | `%LOCALAPPDATA%\Hermes\rag-deps.json` (`rag_extras_verified` fast-path) |
| Future-proof | Eén waarheid: Hermes scripts + Cursor interpreter =zelfde `hermes-env` |

## Eerste installatie

| Startpunt | Script |
| --------- | ------ |
| Hoofd-setup | `SETUP_HERMES.bat` → `setup_hermes_windows.bat` (standaard **--full-setup** → `OPEN_SETUP.bat` wizard). Alleen bestanden: `--files-only` |
| Wizard | `HERMES_SETUP_WIZARD.bat` |
| One-liner (remote) | `scripts/windows/install-J..ps1` (zie `DELEN_MET_VRIENDEN.md`) |

## Dagelijks gebruik

**Hermes starten:** `start_hermes.bat` (repo-root, standaard **full**) → **[START.md](START.md)**, **[LAUNCH_PROFILES.md](LAUNCH_PROFILES.md)**. Terminal/kleuren/muisklik/exit: **[TERMINAL_WINDOWS.md](TERMINAL_WINDOWS.md)**.

### Klassieke CLI — prompt-wachtrij (`/queue`)

Terwijl Hermes bezig is (`display.busy_input_mode: queue` of `/busy queue`):

| Commando | Gedrag |
| -------- | ------ |
| `/queue <prompt>` of `/q <prompt>` | FIFO-wachtrij; ack `[N] Queued: …` |
| `/queue` of `/queue list` | Genummerde lijst in transcript |
| `/queue pop` | Eerste item verwijderen (FIFO) |
| `/queue clear` | Hele wachtrij legen |

**Zichtbaar:** compact paneel boven de invoer (`queued (N)` + max. 2 previews) en `queue:N` in de statusbalk (ook op smalle terminals). Hint verborgen tijdens sudo/approval/clarify/lopend slash-commando. De TUI heeft een rijkere queue-UI (`ui-tui/README.md`).

**Audit:** `audits\RUN_CLI_PENDING_QUEUE_E2E.bat` (17/17, geen live API). Unit: `pytest tests\hermes_cli\test_cli_pending_queue.py` (88 tests).

| Taak | Script |
| ---- | ------ |
| Hermes starten (standaard, volledig) | **`start_hermes.bat`** (SOUL, Docker, dashboard) — [START.md](START.md), [launch_profiles.ps1](launch_profiles.ps1) |
| Hermes starten (snel, alleen chat) | **`start_hermes_minimal.bat`** of `start_hermes.bat --minimal` |
| Debug start | `start_hermes_debug.bat` |
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
| PSES/AST + shell helpers | `tests\Test-PsesTokenizer.ps1`, `tests\HermesShellCommon.Unit.Tests.ps1`, `tests\TrustRuntimePending.Unit.Tests.ps1`, `tests\Invoke-MemoryTrustPostSync.Unit.Tests.ps1`, `audits\RUN_HERMES_SHELL_COMMON_E2E.bat` |
| Profielwissel E2E-audit | `audits\RUN_PROFILE_SWITCH_E2E.bat` |
| SOUL anatomy bij start (stamp) | `launch_soul_anatomy_deploy.ps1` via `launch_hermes.bat` — zie `docs\SOUL_ANATOMY_SPEC.md` |
| SOUL anatomy (handmatig + E2E) | `APPLY_SOUL_ANATOMY_RUNTIME.bat`; alleen snippets: `SYNC_SOUL_SNIPPETS.bat` |
| SOUL deploy-start E2E | `audits\RUN_SOUL_DEPLOY_START_E2E.bat` of `RUN_AUDITS.bat -IncludeSoulDeployStartE2E` |
| SOUL anatomy E2E (runtime) | `audits\RUN_SOUL_ANATOMY_E2E.ps1` |
| SOUL legacy → anatomy | `MIGRATE_SOUL_ANATOMY.bat` |
| Trust & Forensic (legal + SOUL + memory + J.) | `SYNC_TRUST_RUNTIME.bat` — sync + **pre-audit runtime scrub** + audit + gate + /new; `SYNC_TRUST_PROTOCOL.bat` / `APPLY_TRUST_PROTOCOL.bat` — + repo-scrub; `scripts\repair_runtime_identity.ps1` — handmatig; `docs\TRUST_FORENSIC_PROTOCOL.md` |
| Pending trust na mislukte UPDATE | Automatisch bij `start_hermes.bat` via `scripts\launch_pending_trust_runtime.ps1` → `Invoke-TrustRuntimeLight.ps1` (geen pytest-gate); stamp `%LOCALAPPDATA%\hermes\pending_trust_runtime.json`; skip: `HERMES_SKIP_PENDING_TRUST_ON_START=1` |
| Pending trust E2E | `audits\RUN_PENDING_TRUST_START_E2E.bat` of `RUN_AUDITS.bat -IncludePendingTrustStartE2E` |
| Memory-trust integratie E2E | `audits\RUN_MEMORY_TRUST_INTEGRATION_E2E.bat` (10/10: post-sync, pending trust, workspace template, AST, unit tests) |
| Domein-toolsets (minimaal + opt-in) | `SYNC_DOMAIN_TOOLSETS.bat` — `docs\domain_toolsets.yaml`, `docs\DOMAIN_TOOLSET_AUDIT.md` |
| Nieuw profiel (runtime) | `set HERMES_HOME=%LOCALAPPDATA%\hermes` → `SYNC_DOMAIN_TOOLSETS.bat --create-missing` — zie `docs\DOMAIN_BLUEPRINT.md` |
| Provision E2E (smoke) | `audits\RUN_PROVISION_DOMAIN_E2E.bat` |
| Toolset E2E (14 profielen) | `audits\RUN_TOOLSET_DOMAIN_E2E.bat` of `RUN_AUDITS.bat -IncludeToolsetDomainE2E` |
| Web dashboard (9119, geen tab) | Automatisch bij `launch_hermes.bat` (Codebase Viz warmup); uit: `HERMES_SKIP_DASHBOARD_ON_START=1` |
| **Alles-in-één na codewijziging** | `hermes_onderhoud.bat` of `windows\HERMES_ONDERHOUD.bat` (snelkoppelingen + dashboard + Codebase Viz) |
| Snelkoppelingen kapot / `. was unexpected` | `hermes_onderhoud.bat` (of `-ShortcutsOnly`) → taakbalk-pin opnieuw via `Start Hermes - naar taakbalk slepen.lnk` |
| Institutionele presentatie | `docs\INSTITUTIONAL_PRESENTATION.md` |
| Core routing / landkaart | `docs\ORCHESTRATOR_ROUTING.md`, skill `landkaart` (`/landkaart`) |
| Legal lenzen (één bucket) | `docs\LEGAL_DOMAIN_ARCHITECTURE.md`, `docs\LEGAL_TAXONOMY.md`, `MIGRATE_LEGAL_LAYOUT.bat` |
| Legal fork-skills (zoek/parse/web) | `skills\legal\` — `rechtspraak-zoeken`, `uitspraak-parseren`, `web-research-legal`; sync manifest: `SYNC_DOMAIN_TOOLSETS.bat` |
| Repo-hygiene (schone root) | `docs\WORKSPACE_CONVENTIONS.md` · preflight: `scripts\guard_git_clean.ps1` · log: `_upstream_sync_guard.log` |
| QuickFix vóór update | `UPDATE_HERMES.bat -QuickFix` · `scripts\quick_fix_repo_hygiene.ps1` |
| Repo health check | `scripts\health_check_repo.ps1` · `-Strict` voor CI |
| Repo-hygiene E2E | `..\audits\RUN_REPO_HYGIENE_E2E.bat` (9/9) · integratie: `RUN_UPDATE_HERMES_INTEGRATION_E2E.bat` (12/12) |
| RUN_AUDITS repo-hygiene | `audits\RUN_AUDITS.bat -IncludeInstitutionalHardeningE2E` · `-IncludeRepoHygieneE2E` · `-IncludeUpdateHermesIntegrationE2E` |
| POST_GIT_PULL QuickFix | `POST_GIT_PULL.bat -QuickFix` (vóór verify) |
| Legal skills pytest (101) | `pytest tests\skills\test_*_skill.py` · `..\audits\RUN_LEGAL_SKILLS_ROOKTEST.bat` |
| Institutioneel hardening E2E | `..\audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat` (14/14) |
| Gedeelde hygiene helpers | `scripts\RepoHygieneCommon.ps1` |
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
| Python institutioneel E2E | `audits\RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.bat` · zie `docs\HERMES_START.md` |
| Python institutional regressie E2E | `audits\RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat` (review-fixes, 8/8) |
| Institutional productie-poort | `audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` (Python + KnowledgeRepository + platform + **hardening 14/14** + wiring) · `docs\INSTITUTIONAL_OPERATIONS.md` |
| Codebase smoke E2E (E1/E2) | `audits\RUN_CODEBASE_SMOKE_E2E.bat` · `RUN_AUDITS.bat -IncludeCodebaseSmokeE2E` · `-IncludeAllE2E` |
| Codebase smoke (snel) | `audits\RUN_CODEBASE_SMOKE_AUDIT.bat` · `RUN_AUDITS.bat -IncludeCodebaseSmoke` |
| Na `git pull` (aanbevolen) | **`PULL_HERMES.bat`** (repo-root): `git pull` + `POST_GIT_PULL` + **Hermes-relaunch** in WT (`Invoke-HermesPostPullRelaunch.ps1`, `-KeepPid`) |
| Na pull/update (optioneel) | `POST_GIT_PULL.bat -Full` (= AutoRepair + InstitutionalVerify + relaunch) · `-IncludeCodebaseSmoke` / `-IncludeCodebaseSmokeE2E` · `-IncludeRagPipeline` · `-SkipRelaunch` · `HERMES_SKIP_RELAUNCH_AFTER_PULL=1` · `UPDATE_HERMES.bat` |
| Post-pull E2E (geïsoleerd) | `audits\RUN_POST_GIT_PULL_AUTOMATION_E2E.bat` (14/14) · unit: `pytest tests\audits\test_post_git_pull_automation_e2e_harness.py -m "not e2e"` |
| RAG na pull (optioneel) | `windows\RAG_PIPELINE.bat` — readiness (`Get-RagSourceReadiness.ps1`) + ingest; exit 2 = geen bronnen in `%USERPROFILE%\data\raw_source_files` |
| Memory productie-poort | `audits\RUN_MEMORY_PRODUCTION_GATE.bat` (limits + memory + trust E2E + pytest) |
| Memory-architectuur E2E | `audits\RUN_MEMORY_ARCHITECTURE_E2E.bat` (launcher → `MemoryArchitectureE2E.core.ps1`, 18/18) |
| Trust forensic E2E | `audits\RUN_TRUST_FORENSIC_E2E.bat` (launcher → `TrustForensicE2E.core.ps1`) |
| Audit PS1 syntax (IDE) | `audits\VALIDATE_AUDIT_PS1_SYNTAX.bat` |
| Taakbalk-snelkoppelingen vernieuwen | `REFRESH_TASKBAR_SHORTCUTS.bat` of `CREATE_DESKTOP_SHORTCUT.bat` (Start: `wt.exe` + `start_hermes.bat`; overige: `cmd /c` + `call` + gekleurd `.ico`) |

### Eén onderhoudsscript (aanbevolen na wijzigingen)

```cmd
hermes_onderhoud.bat
```

Doet in volgorde: taakbalk-.lnk + bureaublad + pins → pip `[web]` + pygount → `npm run build` (indien nodig) → dashboard 9119 → health + force-scan.

| Vlag | Alleen |
|------|--------|
| `-ShortcutsOnly` | Snelkoppelingen (alias: `REFRESH_TASKBAR_SHORTCUTS.bat`) |
| `-DashboardOnly` | Dashboard/Codebase Viz (alias: `audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat`) |
| `-VerifyChain` | + `VERIFY_WINDOWS_CHAIN` |
| `-OpenCodebaseViz` | Browser-tab `/codebase-viz` |
| `-StartHermes` | Daarna `start_hermes.bat` |

### Overige `.bat`-bestanden

| Soort | Voorbeeld | Wanneer |
|-------|-----------|---------|
| **Dagelijks / start** | `start_hermes.bat` | Chat (+ dashboard warmup bij start) |
| **CI / E2E** | `RUN_AUDITS.bat`, `RUN_CODEBASE_VIZ_*_E2E.bat` | Ontwikkelaars, niet handmatig na elke wijziging |

Oude losse scripts (`REFRESH_*`, `RESTART_CODEBASE_VIZ_*`, `CREATE_DESKTOP_*`) zijn **aliases** naar `HERMES_ONDERHOUD.bat`.
| Taakbalk-icoon herstellen | `FIX_TASKBAR_ICONS.bat` |
| Nous upstream-merge (uitleg) | `UPSTREAM_SYNC.md` |
| Repo-hygiene E2E | `..\audits\RUN_REPO_HYGIENE_E2E.bat` · `..\audits\REPO_HYGIENE_E2E_README.md` |
| Sentence-transformers cache warmen | `scripts/warm_sentence_transformers_cache.bat` |

## Tests

`tests/RUN_PYTEST.bat`, `tests/RUN_PSScriptAnalyzer.bat` — logs staan in `.gitignore`.

**Legal fork-skills (unit, geen netwerk, 101 tests):**

```cmd
%USERPROFILE%\miniconda3\envs\hermes-env\python.exe -m pytest tests\skills\test_rechtspraak_zoeken_skill.py tests\skills\test_uitspraak_parseren_skill.py tests\skills\test_web_research_legal_skill.py -q
```

Mocks: `urllib.request.urlopen`, `time.sleep`, optionele imports (`docx`, `fitz`). Dekking: happy path, edge cases (ongeldige ECLI, lege query, response-truncatie, URL-dedupe), negatieve scenario's (netwerk/import).

**Repo-hygiene + PowerShell E2E (Windows, opt-in via marker `e2e`):**

```cmd
pytest tests\windows\test_repo_hygiene_institutional_e2e.py -m e2e -q
```

Wiring-regressie (snel, standaard pytest): `pytest tests\windows\test_repo_hygiene_institutional_e2e.py -q` (zonder `-m e2e`). Zelfde scenario's als `audits\RUN_*_E2E.bat`.

| Check | Script |
| ----- | ------ |
| `.bat` → `.ps1` ketens + pad-literals | `VERIFY_WINDOWS_CHAIN.bat` → `verify_windows_script_chain.ps1` (geen `windows\scripts` in PS1-strings; voorkomt IDE false positives) |
| SOUL sync / PS helpers | `HermesShellCommon.ps1` + `scripts/SyncSoulSnippet.psm1` — `Test-NativeCommandFailed`, IDE-safe logging; zie `docs/SOUL_ANATOMY_SPEC.md` |
| PS1-onderhoud (tags/exit) | `tools/repair_ps1_write_host_tags.py`, `tools/repair_ps1_native_exit.ps1` |

## Hermes-profielen en model

| Onderwerp | Plek |
| --------- | ---- |
| Model/provider (alle profielen) | `%LOCALAPPDATA%\hermes\config.yaml` — `hermes model` (atomisch via `persist_model_runtime`) |
| Profiel legal/core (MCP) | `%LOCALAPPDATA%\hermes\profiles\<naam>\config.yaml` — **geen** `model:` |
| Auth/config split-brain | `REPAIR_MODEL_PROVIDER.bat` of `hermes doctor --fix` |
| Opruimen oude `model:` in profielen | `DOCTOR_FIX.bat` of `hermes doctor --fix` |

Zie `docs\PROFILE_MODEL_INHERITANCE.md`.

## Configuratie

- `launcher_config.ps1` — paden en omgeving
- `team_display.defaults` — teamweergave (`skin=default`, `final_response_markdown=render`, `assistant_render_style=institutional_rich`, `assistant_palette=demo`, `assistant_label_columns=true`, `compact=false`, `streaming=false`)
- `apply_team_display.ps1` — team display naar **actief profiel** (`profiles\<active>\config.yaml`; root blijft `HERMES_HOME`)
- `audits\RUN_INSTITUTIONAL_E2E.bat` — institutioneel pakket (**11 stappen**, incl. Rich-renderer 2e); zie `audits\README.md`
- **Split-home:** `docs\HERMES_HOME_WINDOWS.md` · drift: `VERIFY_HERMES_CONFIG_DRIFT.bat` (incl. coherence) · migratie: `APPLY_HERMES_HOME_MIGRATION.bat` · E2E: `RUN_HERMES_HOME_E2E.bat`, `RUN_ROOT_CONFIG_INHERITANCE_E2E.bat`, `audits\RUN_MODEL_PROVIDER_COHERENCE_E2E.bat` (`-IncludeModelProviderCoherenceE2E`) · `RUN_MODEL_PROVIDER_HARDENING_E2E.bat` (`-IncludeModelProviderHardeningE2E`)
- `sync_hermes_api_env.ps1` — API-keys + vault-paden (`OBSIDIAN_VAULT_PATH`, `WIKI_PATH`) naar alle profiel-`.env`
- `TERMINAL_WINDOWS.md` — WT, skin, markdown-kleuren, API-home
- `PSScriptAnalyzerSettings.psd1` — lint-regels

**RAG handmatig/taakbalk:** `RAG_KNOWLEDGE_UPDATE.bat` — J/N via typen + Enter, venster blijft open (`cmd /k` in `.lnk`). Regenereer via `FIX_TASKBAR_ICONS.bat` of `create_taskbar_shortcuts.ps1`. **Alleen geplande nacht-run:** `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` (`HERMES_NONINTERACTIVE=1`, geen J/N).

**Iconen (taakbalk + Verkenner):** goud = start/RAG (`hermes_logo.ico`), groen = setup (`hermes_logo_setup.ico`), wit/zilver = update (`hermes_logo_update.ico`), roze = backup, cyaan = restore. Bron: `assets/Hermes_logo.png` (of `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`). Generator bouwt **7-lagen ICO** (16–256 px). Gekleurde varianten in `windows/.gitignore` — na clone: generator + `FIX_TASKBAR_ICONS.bat`. **Start-.lnk:** `wt.exe` + `start_hermes.bat` (`Set-HermesStartShellShortcut`). **Overige .lnk:** `cmd.exe /c` + `cd /d` + `call` (RAG: **`/k`** voor J/N + pause) + `IconLocation` op `.ico` (niet `.bat` slepen). Controle: `scripts/verify_taskbar_shortcut_icons.ps1`. Herstel: `CREATE_DESKTOP_SHORTCUT.bat` of `hermes_onderhoud.bat -ShortcutsOnly` → **F5** in Explorer → taakbalk-pin opnieuw via `.lnk`.
