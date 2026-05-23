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
- [x] Domein-toolsets: `docs/domain_toolsets.yaml`, `DOMAIN_TOOLSET_AUDIT.md`, `SYNC_DOMAIN_TOOLSETS.bat`, `SOUL_SHARED_TOOL_GOVERNANCE`, `RUN_TOOLSET_DOMAIN_E2E.ps1`
- [x] Runtime provision: `--create-missing` in `sync_profile_toolsets_from_manifest.py` (+ `--clone-from`, `--provision-only`, `--sync-soul-snippets`); tests `test_provision_profile_from_manifest.py`; E2E `RUN_PROVISION_DOMAIN_E2E.bat`; skill `create_fork_domain`
- [x] ICT-team profielen: `ict`, `security`, `dev`, `data` — SOUL's, toolsets, RAG-mappen, procedures, E2E PASS
- [x] Upstream-update keten: `windows/upstream_sync.ps1`, `UPDATE_HERMES.bat`, `UPSTREAM_SYNC.md` (+ post-merge git-inspectie + rooktest-matrix, geen handmatig Nous-changelog)
- [x] Taakbalk `windows\*.lnk`: `cmd.exe /c` (+ RAG: `/k`) + gekleurd `.ico` (7 lagen 16–256 px); `FIX_TASKBAR_ICONS.bat`; `POST_GIT_PULL.bat`
- [x] Icoon-generator: PNG uit `assets/Hermes_logo.png` of `%USERPROFILE%\.hermes\_local_assets\assets\`; geen synthetische H-stub
- [x] `SETUP_HERMES.bat` → standaard `--full-setup` + `OPEN_SETUP.bat`; `--files-only` voor alleen bestanden
- [x] `verify_taskbar_shortcut_icons.ps1`; `Set-HermesShellShortcut` / pins in `fix_hermes_taskbar_pins.ps1`
- [x] Setup single source: canoniek `scripts/windows/setup_hermes_windows.ps1`, wrapper `windows/setup_hermes_windows.ps1`, `HermesSetupScriptPolicy.ps1`, pytest `test_setup_single_canonical_ps1.py`
- [x] User-data docs: `%USERPROFILE%\data\STATUS.md`, `RECOVERY.md`; `profiles\core\KANBAN_WORKFLOWS.md`; canoniek `docs/USER_DATA_OPERATIONS.md`
- [x] IDE: `hermes-agent/.vscode/settings.json` + `docs/IDE_VSCODE_SETTINGS.example.json`
- [x] Setup bat-templates (`scripts/windows/bat-templates/`); geen Copy-Item-spiegel meer; PSScriptAnalyzer 0 op `windows/**/*.ps1`
- [x] pytest Windows: `timeout-method=thread`; `shutil.which` i.p.v. `which rg`; marker `ssh` in `pyproject.toml`; `tests/windows/test_critical_windows_scripts.py`
- [x] Python-policy institutioneel: `HermesPythonPolicy.ps1`, `REPAIR_PYTHON.bat`, `ensure_hermes_python.ps1`; kapotte `.venv` → `.venv.disabled-*` (gitignore); conda `hermes-env` canoniek; verify-keten + setup-hook
- [x] TUI display: skin `default` (`team_display.defaults`), `apply_team_display.ps1` → `profiles\<active>\config.yaml` (conda `--env-vars`)
- [x] E2E institutioneel: `RUN_INSTITUTIONAL_E2E.ps1` (**11 stappen + 2f diagnose + 2g score**, PASS 2026-05-23)
- [x] Assistant Rich-renderer: `institutional_render.py` (`TightHeadingBody`, `SectionSpacer`, per-kolom tabellen, labels verticaal — peel uit heading-body)
- [x] Markdown pipeline: `display_markdown.py` + `agent/rich_output.py` + `ChatConsole(get_assistant_console_theme())` in `cli.py`
- [x] Pariteit Ink/Web: `institutionalMarkdown.ts`, `institutionalMarkdownNormalize.ts`, `institutionalColors.ts` (cyaan-first tabelpalet)
- [x] Normalizer-pariteit pytest: `tests/hermes_cli/test_normalizer_ts_parity.py` + `scripts/normalize_assistant_markdown_*_runner.ts` (Python ↔ Web/Ink via `npx tsx`)
- [x] Globaal outputformaat: `SOUL_SHARED_OUTPUT_FORMAT.md` + `SyncSoulSnippet.psm1` (NFR-tabel verplicht)
- [x] Normalizer: outline, institutional_check, NFR prose→tabel (`markdown_output_normalize.py` + TS parity)
- [x] Palet: h2 groen ≠ tabelkolom 0 cyaan (`header_palette` op **alle** YAML-paletten in `config/palettes.yaml`)
- [x] Rooktest: `docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md` (10/10 checklist)
- [x] Web: celkleur per tabelkolom (`tableCellClass` op `<td>`, parity CLI)
- [x] Score/diagnose: `score_institutional_render.py` (**7 checks**, 10.0/10 sample), `diagnose_renderer.py` (kleurlegenda + NFR-prose lint)
- [x] Legal SOUL: NFR-tabel reminder in `docs/templates/SOUL_LEGAL_DOMAIN.md`
- [x] Labels checklist #5: waarde onder label (CLI peel + Web `flex-col`); inline `**Label:** waarde` via normalizer + renderer (rooktest 10/10)
- [x] Nieuwe-chat vlag na SOUL-sync: `institutional_new_chat_notice.py` + banner in `cli.py`
- [x] Tests: `test_institutional_rich_render.py`, `test_markdown_output_normalize.py`, `test_institutional_production.py`
- [x] Team display: `compact=false`, `render`, `skin=default` (`team_display.defaults`)
- [x] Docs: `docs/INSTITUTIONAL_PRESENTATION.md`; legacy `windows/scripts/institutional/`
- [x] Split Hermes-home: `sync_hermes_api_env.ps1` + `SYNC_HERMES_API_ENV.bat`; docs `TERMINAL_WINDOWS.md`
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
3. **Verify:** `python scripts/diagnose_renderer.py` + `python scripts/score_institutional_render.py --verify`
4. Bronnen in 7 lege `raw_source_files`-mappen
5. `institutional_p0_p1.bat --ingest-remaining`
6. `update_knowledge.bat --mcp-test`
7. Geen ingest + Kanban tegelijk op dezelfde LanceDB (lock)

## Bekende valkuilen

- Ingest + Kanban parallel op `lancedb/legal` → LanceDB-lock / corruptie-risico
- Zonder ingest = lege index; zonder Hermes-profiel + MCP = agent weet niet waar te zoeken
- `model:` in `profiles/<naam>/config.yaml` is verouderd — gebruik root config + `docs/PROFILE_MODEL_INHERITANCE.md`
- Zie `docs/RAG_TWEE_FASEN.md` en `docs/README.md` voor volledige uitleg
