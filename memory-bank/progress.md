# Progress

## Code (P2 + institutioneel)

- [x] `pyproject.toml` extra `[rag]` (+ faster-whisper)
- [x] pytest `tests/rag_pipeline/` + integratie `rag_integration`
- [x] Multi-domein ingest (`run_domains_ingest.py`, `domains_config.py`, `domains.yaml`)
- [x] Quarantaine-restore (`source_layout.py`, `quarantine_restore` in yaml)
- [x] Media-beleid Whisper (`media_policy: whisper_when_missing` voor legal)
- [x] Eindrapport na ingest (`ingest_run_summary.py` → `rag_ingest_run_summary.json`)
- [x] Live status institutioneel (`ingest_live_status.py`: run_state, finalize, reconcile)
- [x] HTML-fallback na MarkItDown-fout
- [x] MCP per profile (`lancedb-<domein>`) — **`mcp_servers:`** (sync: `sync_profile_mcp_from_domains.py`)
- [x] Institutionele P0-pipeline (`windows/scripts/institutional_p0_p1.bat`)
- [x] Profiel-model overerving (`profile_model_inheritance.py`, docs, doctor `--fix`, tests)
- [x] Windows launchers (`update_knowledge.bat` / `.ps1`, `windows/scripts/rag/`)
- [x] Noob-doc `docs/RAG_TWEE_FASEN.md` (bibliotheek vs. balie, twee fasen)
- [x] Taakbalk RAG interactief: `RAG_KNOWLEDGE_UPDATE.bat` + `.lnk` `cmd /k` (J/N via `set /p`); nacht: `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` (`HERMES_NONINTERACTIVE=1`)
- [x] Trust & Forensic: `SOUL_SHARED_ADVISORY`, legal forensic-blok, `MEMORY_CANONICAL_SEED`, `SYNC_TRUST_RUNTIME` / `APPLY_TRUST_PROTOCOL`, scrub (gericht), `RUN_TRUST_FORENSIC_E2E`, legal E2E stap 3/8 memories
- [x] SOUL Anatomy: `SOUL_ANATOMY_SPEC`, 13× `SOUL_*_DOMAIN` + core orchestrator, shared VALUES/WORKFLOW/MEMORY/TRUST, sync + `migrate_soul_anatomy.ps1`, `validate_soul_anatomy.py`, `RUN_SOUL_ANATOMY_E2E.ps1`, `RUN_SOUL_DEPLOY_START_E2E.ps1`; stamp-deploy `launch_soul_anatomy_deploy.ps1` (start + POST_GIT_PULL); runtime `APPLY_SOUL_ANATOMY_RUNTIME.bat`; output-sync insert + duplicate-repair (2026-05-23)
- [x] SOUL snippet-sync robuustheid: `Test-NativeCommandFailed` in `SyncSoulSnippet.psm1` + orchestrator/deploy/institutional/sync_all; alle `sync_soul_*_snippet.ps1` met `exit 0`; verify-keten pad-literals `/`; IDE/PSES parser-hygiëne (2026-05-23)
- [x] SOUL governance: zekerheid %, gaps/strategie, ga-door 1/N, tool 1× retry, geen compromis; `SOUL_ROOT_FALLBACK` + `sync_root_soul_fallback.ps1`; `validate_soul_anatomy.py --check-governance`; `docs/SOUL_GOVERNANCE.md` (2026-05-23)
- [x] Windows split-home runtime: `HermesHomeCommon.ps1`, drift/migratie/E2E, doctor + `hermes config get`, `HERMES_WIN_PREFER_LOCALAPPDATA`, `docs/HERMES_HOME_WINDOWS.md` (2026-05-23; **machine + audits groen 2026-05-24**)
- [x] `HermesShellCommon.ps1`: gedeelde `Test-NativeCommandFailed` + `Write-Hermes*`; hele `windows/**/*.ps1` IDE-safe `[TAG]`-logging + native-exit checks; repair-tools in `windows/tools/` (2026-05-23)
- [x] Domein-toolsets: `docs/domain_toolsets.yaml`, `DOMAIN_TOOLSET_AUDIT.md`, `SYNC_DOMAIN_TOOLSETS.bat`, `SOUL_SHARED_TOOL_GOVERNANCE`, `RUN_TOOLSET_DOMAIN_E2E.ps1`
- [x] Runtime provision: `--create-missing` in `sync_profile_toolsets_from_manifest.py` (+ `--clone-from`, `--provision-only`, `--sync-soul-snippets`); tests `test_provision_profile_from_manifest.py`; E2E `RUN_PROVISION_DOMAIN_E2E.bat`; skill `create_fork_domain`
- [x] ICT-team profielen: `ict`, `security`, `dev`, `data` — SOUL's, toolsets, RAG-mappen, procedures, E2E PASS
- [x] Upstream-update keten: `windows/upstream_sync.ps1`, `UPDATE_HERMES.bat`, `UPSTREAM_SYNC.md` (+ post-merge institutional runtime, git-inspectie + rooktest-matrix)
- [x] Upstream merge 2026-05-23: 58 Nous-commits, 1 conflict (CI tests.yml), E2E PASS — `windows/audits/UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md`
- [x] `MERGE_UPSTREAM.bat` + IDE-prompt (`merge_upstream_fork.ps1`); default IDE-guided, `-AutoResolve` opt-in
- [x] Merge `-PromptOnly`: git-diff snippets per conflict (`Get-ConflictSnippetForPrompt`, `Get-ConflictSnippetFromGitDiff`)
- [x] LanceDB onderhoud: `scripts/rag_pipeline/lancedb_maintenance.py`, `windows/LANCEDB_MAINTENANCE.bat` (list/inspect/init-missing/compact/benchmark)
- [x] `domains.yaml` user-data: 13 domeinen (ict/security/dev/data); lege LanceDB via `--init-missing`
- [x] Skill drift audit: `scripts/audit_skill_drift.py` → `windows/audits/SKILL_DRIFT_AUDIT_*.md`
- [x] IDE conda: `.vscode/settings.json` + `.cursor/rules/python-conda.mdc` + `docs/IDE_VSCODE_SETTINGS.example.json`
- [x] IDE-onderhoud baseline/audit: `windows/audits/IDE_MAINTENANCE_BASELINE_2026-05-23.md`, `LANCEDB_SCHEMA_AUDIT_*.md`
- [x] IDE-onderhoud E2E: `RUN_IDE_MAINTENANCE_E2E.ps1` + `.bat` (15 stappen landkaart, rapport `IDE_MAINTENANCE_E2E_REPORT_*.md`); `RUN_AUDITS -IncludeIdeMaintenanceE2E`
- [x] Memory productie-poort: `RUN_MEMORY_PRODUCTION_GATE.ps1` + `.bat`; trust limits 4000/1800 alle profielen; `MemoryAuditCommon.ps1`, `audit_profile_memories.ps1`
- [x] Trust E2E PSES-refactor: launcher + `TrustForensicE2E.core.ps1`; manifest-paden in `HermesCriticalWindowsRepoPaths.ps1`; `VALIDATE_AUDIT_PS1_SYNTAX.bat`
- [x] Memory E2E PSES-refactor: launcher + `MemoryArchitectureE2E.core.ps1` (18/18: legacy root, consolidatie-layout, § U+00A7); idem validate-lijst
- [x] Obsidian L4-automatisering: `OPEN_OBSIDIAN_VAULT.bat`, `open_obsidian_vault.ps1`, `ensure_hermes_knowledge_vault.ps1`, scaffold-template, taakbalk-rol `Obsidian`, sync in `sync_hermes_api_env.ps1`
- [x] Memory-consolidatie institutioneel: `HermesMemoryMergeCommon.ps1`, `CONSOLIDATE_ROOT_MEMORIES.bat`, rebalance Hermes-config → core; `deduplicate_memories.py` (+ legacy root); core/legal domein-scheiding; audit PASS alle 13 profielen + legacy root; production gate PASS
- [x] TUI statusbalk-kosten (rich): defaults `show_cost`/`cost_bar_mode`; `statusRuleColumns` (composer-padding); altijd zichtbaar + gereserveerd segment; live `~$turn`/`~NK tok`; breakdown-tier ≥72 cols; E2E `RUN_STATUS_BAR_COST_E2E`
- [x] Klassieke CLI statusbalk-kosten: layout reorder (kosten na ctx/duur/timer), `status-bar-cost` (gedimd blauw), `session_tool_executions`; Gemini cache catalog + `_seed_agent_session_cost`; E2E **12/12**
- [x] OpenRouter Pareto Code router E2E: `RUN_PARETO_E2E.bat` (8 stappen), `verify_pareto_router.py`, `test_pareto_e2e.py`
- [x] Codebase-audit smoke vs release: `CODEBASE_AUDIT_EVIDENCE.md`, templates, `RUN_CODEBASE_SMOKE_AUDIT.ps1/.bat`, `RUN_CODEBASE_SMOKE_E2E`, `emit_codebase_smoke_report.py`, `RUN_AUDITS -IncludeCodebaseSmoke`; optioneel na pull/update: `POST_GIT_PULL`/`UPDATE_HERMES` + `Invoke-PostSyncCodebaseSmoke.ps1`; SOUL + `validate_soul_anatomy --check-codebase-audit-claims`
- [x] Taakbalk `windows\*.lnk`: `cmd.exe /c` (+ RAG: `/k`) + gekleurd `.ico` (7 lagen 16–256 px); `FIX_TASKBAR_ICONS.bat`; `POST_GIT_PULL.bat`
- [x] Icoon-generator: PNG uit `assets/Hermes_logo.png` of `%USERPROFILE%\.hermes\_local_assets\assets\`; geen synthetische H-stub
- [x] `SETUP_HERMES.bat` → standaard `--full-setup` + `OPEN_SETUP.bat`; `--files-only` voor alleen bestanden
- [x] `verify_taskbar_shortcut_icons.ps1`; `Set-HermesShellShortcut` / pins in `fix_hermes_taskbar_pins.ps1`
- [x] Setup single source: canoniek `scripts/windows/setup_hermes_windows.ps1`, wrapper `windows/setup_hermes_windows.ps1`, `HermesSetupScriptPolicy.ps1`, pytest `test_setup_single_canonical_ps1.py`
- [x] Backup schema v3 (2026-05-23): `HermesBackupCommon.ps1`, `runtime_hermes/` + `legacy_hermes/` + persona-subset; safe-for-backup gate; restore `-RestoreRuntimeFull`; test `RUN_BACKUP_E2E.bat`
- [x] IDE: `hermes-agent/.vscode/settings.json` + `docs/IDE_VSCODE_SETTINGS.example.json`
- [x] Setup bat-templates (`scripts/windows/bat-templates/`); geen Copy-Item-spiegel meer; PSScriptAnalyzer 0 op `windows/**/*.ps1`
- [x] pytest Windows: `timeout-method=thread`; `shutil.which` i.p.v. `which rg`; marker `ssh` in `pyproject.toml`; `tests/windows/test_critical_windows_scripts.py`
- [x] PSScriptAnalyzer `windows\`: 0 Warning/Error (2026-05-23) — unused params/vars, ShouldProcess, catch-blokken, merge `-LockTheirs` wiring
- [x] Python-policy institutioneel: `HermesPythonPolicy.ps1`, `REPAIR_PYTHON.bat`, `ensure_hermes_python.ps1`; kapotte `.venv` → `.venv.disabled-*` (gitignore); conda `hermes-env` canoniek; verify-keten + setup-hook
- [x] TUI display: skin `default` (`team_display.defaults`), `apply_team_display.ps1` → `profiles\<active>\config.yaml` (conda `--env-vars`)
- [x] E2E institutioneel: `RUN_INSTITUTIONAL_E2E.ps1` (**11 stappen + 2f diagnose + 2g score + 2h pseudo-tabel**, PASS 2026-05-23)
- [x] Assistant Rich-renderer: `institutional_render.py` (`TightHeadingBody`, `SectionSpacer`, per-kolom tabellen, labels verticaal — peel uit heading-body)
- [x] Markdown pipeline: `display_markdown.py` + `agent/rich_output.py` + `ChatConsole(get_assistant_console_theme())` in `cli.py`
- [x] Pariteit Ink/Web: `institutionalMarkdown.ts`, `institutionalMarkdownNormalize.ts`, `institutionalColors.ts` (cyaan-first tabelpalet)
- [x] Normalizer-pariteit pytest: `tests/hermes_cli/test_normalizer_ts_parity.py` + `scripts/normalize_assistant_markdown_*_runner.ts` (Python ↔ Web/Ink via `npx tsx`)
- [x] Globaal outputformaat: `SOUL_SHARED_OUTPUT_FORMAT.md` + `SyncSoulSnippet.psm1` (NFR-tabel verplicht)
- [x] Normalizer: outline, institutional_check, NFR prose→tabel, **pseudo-tabel/underscore vs→markdown** (`ensure_markdown_table_dividers`, `normalize_pseudo_tables_to_markdown`; max 6 kolommen contextafhankelijk)
- [x] Palet: h2 groen ≠ tabelkolom 0 cyaan (`header_palette` op **alle** YAML-paletten in `config/palettes.yaml`)
- [x] Rooktest: `docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md` (10/10 checklist)
- [x] Web: live `assistantPalette` via `GET /api/display/assistant` + `AssistantDisplayProvider` (commit `19239a6fd`)
- [x] Score/diagnose: `score_institutional_render.py` (**8 checks** incl. `vergelijking_tabel`, 10.0/10 sample), `diagnose_renderer.py` (kleurlegenda + NFR + pseudo-tabel self-test); **E2E** `RUN_PSEUDO_TABLE_NORMALIZER_E2E.bat` (10/10 PASS), `verify_pseudo_table_normalizer.py --verify`
- [x] Legal SOUL: NFR-tabel reminder in `docs/templates/SOUL_LEGAL_DOMAIN.md`
- [x] Labels checklist #5: waarde onder label (CLI peel + Web `flex-col`); inline `**Label:** waarde` via normalizer + renderer (rooktest 10/10)
- [x] Nieuwe-chat vlag na SOUL-sync: `institutional_new_chat_notice.py` + banner in `cli.py`
- [x] Tests: `test_institutional_rich_render.py`, `test_markdown_output_normalize.py`, `test_institutional_production.py`
- [x] Team display: `compact=false`, `render`, `skin=default` (`team_display.defaults`)
- [x] Docs: `docs/INSTITUTIONAL_PRESENTATION.md`; legacy `windows/scripts/institutional/`
- [x] Split Hermes-home: `sync_hermes_api_env.ps1` + `SYNC_HERMES_API_ENV.bat` (API + vault naar alle profielen; UPDATE/POST_GIT_PULL/SYNC_TRUST)
- [x] Memory L4 vault: `Hermes Knowledge` + `docs/MEMORY_ARCHITECTURE.md`; E2E `RUN_MEMORY_ARCHITECTURE_E2E.bat` (**16 stappen**, PASS)
- [x] TUI auto `/new` na trust-sync: `newChatNotice.ts`, `useInstitutionalNewChatAutoReset`, `gateway.ready` hook; vitest
- [x] §-dedup preamble + mojibake: `deduplicate_content()` + `tests/scripts/test_deduplicate_memories.py`
- [x] Memory E2E stap 14: alle profielen MEMORY/USER binnen limiet (`Test-AllProfileMemoryFileSizes`)
- [x] Production gate pytest: 55 tests (dedup + institutional notice + trust docs)
- [x] Profielwissel productie: `profile_switch.py`, `/profile use` + `-p` relaunch, `SWITCH_PROFILE.bat`, E2E `RUN_PROFILE_SWITCH_E2E.bat`, `docs/PROFILE_SWITCH.md`
- [x] Profielwissel v2: `_apply_profile_override` sticky>stale env, kanban reclaim, `RUN_AUDITS.ps1`, `test_profile_switch_e2e.py` (HERMES_PROFILE_E2E=1)
- [x] Optimalisatiepakket: `ORCHESTRATOR_ROUTING.md`, skill `landkaart`, `backup_soul_profiles.ps1`, `SYNC_SOUL_SNIPPETS.bat`, UPDATE-uitleg + verify zonder pause, RAG pin-docs
- [x] Legal domein future-proof: `LEGAL_DOMAIN_ARCHITECTURE.md`, `LEGAL_TAXONOMY.md`, `SOUL_LEGAL_DOMAIN.md`, runtime generieke legal-SOUL + `LEGAL_ACTIVE_MATTERS.md`
- [x] Bron-submappen `04_Legal_Corporate` (Arbeidsrecht, Klokkenluiders, …); `migrate_legal_source_layout.ps1`
- [x] `sync_legal_lens_table_from_taxonomy.py`; `RUN_LEGAL_DOMAIN_E2E.bat`; `RUN_AUDITS -IncludeLegalDomainE2E`

## Operationeel (gebruiker)

### Legal — architectuur (2026-05)

- [x] Generieke legal-SOUL + lenzen; GCR in `LEGAL_ACTIVE_MATTERS.md`
- [x] Submappen rechtsgebied onder `04_Legal_Corporate`
- [ ] Optioneel: `update_knowledge.bat legal` na grote bron-migratie (re-index)

### Legal — ingest (2026-05-21)

- [x] **1665/1665** bronnen geïndexeerd (`all_sources_indexed: true`, `skipped_total: 0`)
- [x] 40 media met Whisper (laatste run: 40 geïndexeerd, 1625 unchanged)
- [x] Verzoekschrift-PDF’s op canoniek pad onder `Geschillencommissie Rijk/...`
- [x] Eindrapport: `%USERPROFILE%\data\lancedb\legal\rag_ingest_run_summary.json`
- [x] Rooktest `search_knowledge` op legal LanceDB (2026-05-21, hits met `[Bron: …]`)
- [x] Rooktest `hermes -p legal` chat (2026-05-21; `search_knowledge` + `[Bron: …]` via `institutional_p0_p1.bat`)
- [x] Kanban legal: taak `t_9f206226` **done** (2026-05-21; analyse actieve zorgplicht + `[Bron: Productie 28 -.pdf]`)

### Overige domeinen

- [x] **core** — kleine ingest gedaan
- [x] `--ingest-remaining` met `--skip-empty` (2026-05-21): 7 domeinen overgeslagen (0 bronbestanden); geen crash/pause
- [ ] **Bronnen plaatsen** in lege `raw_source_files`-mappen (nu 0 bestanden: `01_Academics_Beta` … `08_Ventures_Incubator`; legal onder `04_Legal_Corporate` = klaar), daarna `institutional_p0_p1.bat --ingest-remaining`
- [x] Preflight: `scripts/rag_pipeline/ingest_preflight.py` (in `institutional_p0_p1.bat --ingest-remaining`)
- [x] `--mcp-test` (2026-05-21): legal + core OK; 7 domeinen WARN = lege LanceDB (**geen brondata** in `raw_source_files`, geen pipeline-fout)

### Split-home (Windows — 2026-05-24)

- [x] Legacy `~/.hermes/config.yaml` gearchiveerd; `CONFIG_README.txt` aanwezig
- [x] Auxiliary hybrid preset (Qwen local + Gemini vision)
- [x] `APPLY_HERMES_HOME_MIGRATION.bat` — geautomatiseerde keten (backup + deprecate + preset + E2E)
- [x] `RUN_HERMES_HOME_E2E.bat` PASS; drift-check groen
- [x] User `HERMES_HOME` = `%LOCALAPPDATA%\hermes`; gateway aligned

### Config (buiten repo — correct)

- `%USERPROFILE%\data\domains.yaml` — niet committen
- Voorbeeld in repo: `docs/domains.yaml.example`

### Scripts (user data)

- [x] `check_ingest_status.bat` — leest `rag_ingest_run_summary.json` + `rag_ingest_live_status.json`
- [x] `kanban_legal_zorgplicht.bat` — `HERMES_HOME` → profiel `legal`
- Forwarders `update_knowledge_*.bat` → repo via `_forward_to_repo.bat`

## Sluit-checklist (aanbevolen volgorde)

1. ~~Legal rooktest~~ / ~~Kanban legal~~ — afgerond (2026-05-21)
2. **Institutioneel 10/10:** `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` → `/new` → rooktest `docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md` (visueel + score)
3. **Verify:** `python scripts/diagnose_renderer.py --verify` + `python scripts/score_institutional_render.py --verify`; vóór commit renderer-wijzigingen: `python scripts/verify_institutional_guard.py`
4. Bronnen in 7 lege `raw_source_files`-mappen
5. `institutional_p0_p1.bat --ingest-remaining`
6. `update_knowledge.bat --mcp-test`
7. Geen ingest + Kanban tegelijk op dezelfde LanceDB (lock)

## Bekende valkuilen

- Ingest + Kanban parallel op `lancedb/legal` → LanceDB-lock / corruptie-risico
- Zonder ingest = lege index; zonder Hermes-profiel + MCP = agent weet niet waar te zoeken
- `model:` in `profiles/<naam>/config.yaml` is verouderd — gebruik root config + `docs/PROFILE_MODEL_INHERITANCE.md`
- Zie `docs/RAG_TWEE_FASEN.md` en `docs/README.md` voor volledige uitleg
