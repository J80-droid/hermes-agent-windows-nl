# Active context

## Focus

**RUN_AUDITS E2E-keten (2026-05-29, gecommit `74ae0f4e6`):** Gateway cost/tps defensive read; CLI `config get` + profile switch flags; SOUL Output conventions repair; Memory Repair Trust `Initialize-*`; `.gitignore` audit-logs/checkpoint fixtures. `RUN_AUDITS -IncludeAllE2E` roept nu **`soul-runtime-prep`** aan (`sync_all_domain_souls_from_templates -UpdateDeployStamp`) vóór E2E — geen handmatige `APPLY_SOUL_ANATOMY_RUNTIME` meer nodig voor volledige audit. Volledige `-IncludeAllE2E` / `RUN_FULL_VERIFICATION` — zie laatste `audits/RUN_AUDITS_LAST_RUN.log` / `FULL_VERIFY_*.log`.

**Codebase Viz pygount pre-warm + disk-cache (2026-05-29):** `scripts/warm_codebase_viz_pygount_cache.py` + `Ensure-CodebaseVizPygountCache` vóór dashboard; skip `backups/` + `.venv.disabled*`; disk-cache met git-HEAD-validatie + atomic write; E2E **`RUN_CODEBASE_VIZ_PYGOUNT_CACHE_E2E.bat` (8/8)**; defaults 600s/3600s/300s; skip: `HERMES_CODEBASE_VIZ_PREGOUNT_CACHE=skip`.

**Institutionele hardening — productieniveau (2026-05-26, PASS):** `RepoHygieneCommon.ps1`; guard + QuickFix + health check; `UPDATE_HERMES.bat` / `POST_GIT_PULL.bat -QuickFix` (HERMES_WIN shift-safe); guard-log met trim; legal skills (rate limit, 2MB cap, ECLI); pytest **101** + `test_repo_hygiene_institutional_e2e.py`; E2E **14/14**; `RUN_AUDITS` vlaggen (`-IncludeInstitutionalHardeningE2E`, `-IncludeRepoHygieneE2E`, `-IncludeUpdateHermesIntegrationE2E`); CI `fork-windows-institutional.yml`; pre-commit warn-only; productie-poort **PASS**. **Cheat sheet:** `docs/INSTITUTIONAL_OPERATIONS.md#handige-commandos-fork` (canonical; gekoppeld vanuit README, AGENTS, windows/README, docs/README, repo-hygiene.mdc).

**Performance-architectuur RAG + runtime (2026-05-25, PASS):** LanceDB via `KnowledgeRepository.session()` (schema_migrate, bootstrap); enkelvoudige `collect_indexed_files`; `ingest_chunking` + `document_converter`; MCP `_ensure_mcp_knowledge`; batched orphan cleanup; `config_snapshot` + gateway/sandbox mtime-cache; `review_snapshot` (`HERMES_BG_REVIEW_MAX_MESSAGES`); Whisper-cache; `process_registry` pipe-close + Windows PTY fixes (`_pty_spawn_argv`, winpty str-write, detached taskkill, PTY reconcile); mcp stderr-log close. Unit tests RAG +83; `test_process_registry` 60 passed / 6 skipped (Windows). E2E **10/10** `RUN_PERFORMANCE_ARCHITECTURE_E2E.bat` (pytest incl. process_registry). Gate-rapporten `*_PRODUCTION_GATE_REPORT_*.md` gitignored. Refactor: `ingest_handlers`, `bootstrap_ingest_state`, `ingest._plan_incremental_ingest`.

**Platform hardening 10/10 (2026-05-25):** VectorStore-laag (`vector_store_*`, `lancedb_backend`), `KnowledgeRepository` (47 unit tests), regression E2E **10/10**, dedicated `RUN_KNOWLEDGE_REPOSITORY_E2E.bat` **8/8**, productie-poort `RUN_PLATFORM_HARDENING_PRODUCTION_GATE.bat`. Sandbox env-cache bust; hardware `reset_hardware_backend_cache()`; `patch_tool` her-propageert `PermissionError`. Docs: `docs/WINDOWS_PLATFORM_HARDENING.md`.

**Python institutioneel review-fixes (2026-05-25):** bootstrap stamp alleen na succesvolle RAG-sync; `rag-deps.json` fast-path (`rag_extras_verified`); REPAIR non-interactive; `HERMES_CONDA_ROOT`; `Test-HermesPythonHasPip`/`Test-HermesRagExtrasInstalled` catch op ongeldige stub-`.exe`; regression E2E **8/8** (`RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E`); pytest `test_hermes_python_institutional.py` **40 passed**. Runbook: `docs/INSTITUTIONAL_OPERATIONS.md`.

**Split-home & root inheritance (2026-05-25, productie-niveau — AF):** `model` + `auxiliary` + `providers` overerving; Venice merge + env sync; save-guard + cache-bust; keten `APPLY_HERMES_HOME_MIGRATION.bat` (7 stappen); E2E **14/14** (`RUN_HERMES_HOME_E2E`) + **10/10** (`RUN_ROOT_CONFIG_INHERITANCE_E2E`, harness + `py_compile` guard). Runbook: `docs/HERMES_HOME_WINDOWS.md`.

**Model/provider coherentie (2026-05-25, productie-af + hardening):** `persist_model_runtime()` schrijft atomisch naar root + sync `auth.active_provider`; `detect_model_provider_incoherence` / `repair_model_provider_coherence`; doctor `--fix` (ook `strip_all_profile_global_blocks`); setup blokkeert skip bij split-brain; `windows\REPAIR_MODEL_PROVIDER.bat`; `POST_GIT_PULL.bat -AutoRepairModelProvider` (opt-in); `read_auth_json` / nous shared store UTF-8 BOM-safe; gateway `HERMES_STRICT_CONFIG_COHERENCE=1` (opt-in). E2E `RUN_MODEL_PROVIDER_COHERENCE_E2E.bat`; drift via `verify_hermes_config_drift.ps1`. **Operationeel na deploy:** Hermes/gateway herstart + `/new` op gebruikersmachine.
**Model-catalog startup hardening (2026-05-27):** `Test-HermesModelCatalogAvailability` blokkeert startup bij invalid `model.default` t.o.v. provider-catalog met concrete fallback-hint; opt-in self-heal via `HERMES_AUTOREPAIR_MODEL_CATALOG=1` (`Invoke-HermesModelCatalogAutoRepair` persist fallback deterministisch met `persist_model_runtime`), daarna her-validatie.
**Windows WT titelbalk-muis overlay (2026-05-30, OPGELOST + geverifieerd):** `ExpandConsoleToWorkArea` niet meer in `WT_SESSION` (root cause onzichtbare conhost op minimize/close); `RestoreConsoleFromWorkAreaOverlay`, `Invoke-HermesFixMouseBlocked`, `FIX_MOUSE_BLOCKED.bat`/`RESET_TERMINAL.bat`; deferred dashboard `Start-HermesDashboardAfterChatDetached`; geen auto-browser (`HERMES_SKIP_DASHBOARD_BROWSER`, leeg `OPEN_PATH`); docs `windows/MOUSE_OVERLAY_FIX.md`. Zie `TERMINAL_WINDOWS.md`. **Lacunes 1–16 (docs/guards):** memory bank sync, `.cursorrules`, START/LAUNCH_PROFILES, pytest WT-guard, `RUN_WT_MOUSE_OVERLAY_E2E.bat`, Clear-Host in WT, README-FORK, workspace-conventies, doc-drift `docs/*`.

**Startup UX/flow polish (2026-05-27):** dubbele model-catalog FAIL op launcher-start voorkomen door `launch_institutional_runtime.ps1 -SkipConfigDrift` in `launch_hermes.bat`; dashboard deferred na chat; zie bovenstaand overlay-fix.

**Windows chat-startfix (2026-05-27):** `TERM=xterm-256color` verwijderd; `hermes_chat.cmd`; orchestrator + quick dashboard; banner-parser zonder `(?ms).*` (fix hang na config-pad); model-banner alleen in `run_hermes_prepare`; zie `TERMINAL_WINDOWS.md`.

**Windows snelkoppelingen (2026-05-28):** `Set-HermesStartShellShortcut` (WT + `start_hermes.bat`); bureaublad niet meer overschreven door logo-only launcher; `HERMES_ONDERHOUD.bat` + `hermes_onderhoud.bat` (cmd-parsefix `(exit %ERR%)`); docs `START.md` / README / `TERMINAL_WINDOWS.md`.

**Taakbalk alle rollen via WT (2026-05-27):** `Set-HermesShellShortcut` = `wt.exe` + `Get-HermesWtShortcutArgumentLine` (fix cmd-geneste quotes onder WT-default-terminal); `verify_hermes_shortcut_paths.ps1`; `UPDATE_HERMES.bat` preflight via `%~dp0upstream_sync.ps1`; upstream preflight `-Force` / `HERMES_UPSTREAM_AUTO_CONFIRM=1`.

**Launch-profielen (2026-05-28):** `windows/launch_profiles.ps1`; **standaard full**; `start_hermes_minimal.bat` voor snelle chat; CLI-vlaggen gefilterd vóór `hermes_cli`; docs `START.md` + `LAUNCH_PROFILES.md`.

**Post-pull automatisering (2026-05-28):** `start_hermes.bat` = **één entrypoint** — auto-pull alleen als achter tracking branch (`Test-HermesGitPullNeeded.ps1`); anders direct start. `--pull` / `--sync` / `--no-pull`; `PULL_HERMES.bat` = alias `--pull`. `POST_GIT_PULL.bat` (relaunch via `Invoke-HermesPostPullRelaunch.ps1` + WT, `-KeepPid`); trust pending bij FAIL; UPDATE post-merge zelfde relaunch; CLI `_apply_post_sync_new_chat_notice`. E2E **14/14** + unit **56** harness; `test_hermes_git_pull_needed.py`.

**Sessie-onderhoud (2026-05-28):** `launch_hermes.bat` → `launch_hermes.ps1` → `launch_pre_chat_orchestrator.ps1` (bootstrap in orchestrator; `-AllowFailure` dot-source); `HermesSessionMaintenance.ps1` + stamps `%LOCALAPPDATA%\hermes\stamps\`; start: shortcut/TUI/drift-warn/model-repair; POST PostPullTail (toolsets, LanceDB, TUI, pins, smart RAG); `post_pull_maintenance` stamp dedupe (~15 min, zelfde head); `--sync -SkipRelaunch` + `Clear-HermesUpdateCheckCache`; `Invoke-HermesModelCatalogAutoRepair` (-RepoRoot); E2E **14/14** `audits/RUN_SESSION_MAINTENANCE_E2E.bat`; unit `HermesSessionMaintenance.Unit.Tests.ps1` + pytest harness.

**Launch UI Sink (2026-05-29):** `HermesLaunchUi.ps1` + `launch_hermes.ps1` als PS-entry; enkelvoudige console-schrijver (EL `[2K`), capture naar log, rich visual in WT; vaste goudgele kop `Write-HermesLaunchPinnedHeader` (`[93m]` regels 1–2) tijdens spinner; bootstrap via orchestrator (geen `-SkipBootstrap` in bat); E2E **8/8** `audits/RUN_LAUNCH_UI_SINK_E2E.bat` (geen live muis/WT); zie `windows/TERMINAL_WINDOWS.md`.

**Persistente snelkoppelingen (2026-05-29):** `HermesPersistentShortcuts.ps1` + `Invoke-HermesShortcutSyncRepair` — canonieke `.lnk` in `%LOCALAPPDATA%\Hermes\shortcuts\`; taakbalk/bureaublad automatisch bij update/start; icoon-cache via echte `LocalApplicationData` (fix wit document na unit tests); `Repair-HermesBatPathForRepo` voor verplaatste repo-paden.

**Web UI clean codebase (2026-05-29):** `web/` — `npm run lint` + `npm run build` groen; React-hooks fixes (sidebar tooltips via `useTooltipAnchor`, drop-up via `useDropUpFixedStyle`); i18n/theme context gesplitst; Chat PTY-channel `resume-{sessionId}` (geen `:` t.o.v. `_VALID_CHANNEL_RE`); `apply_team_display_profiles.py` utils-import via `sys.path`; E2E **11/11** `audits/RUN_WEB_UI_CLEAN_E2E.bat`; docs `web/README.md`. **A11y/hints (zelfde dag):** listbox-structuur Theme/Language switcher; `lib/aria.ts`; CSS surface utilities (`index.css`); Edge Tools axe-hints (aria strings, geen header in listbox); pytest curses guardrails UTF-8 + clamped-color regex op Windows.

**Upstream sync fase 2 + TUI layout (2026-05-25):** `Invoke-UpstreamGitMergeIfBehind` (preflight fetch-dedup, `$upstreamRef`, rev-list exit guards); `pip install -e .` na merge vóór `hermes update`; TUI `statusRuleMinLeftWidth` + `leftWidth`; slash **`/cost`** + upstream **`/queue`**. E2E **8/8** Phase2 + **7/7** `RUN_HERMES_SHELL_COMMON_E2E` (PSES). **UPDATE 2026-05-25:** 15 commits merge (conflict `core.ts` opgelost), daarna 2 commits auto-merge + volledige keten OK. **PSES:** `HermesShellCommon` `INFO:`/`OK:` tags, `Format-HermesStepLabel`, `Test-PsesTokenizer` 12 scripts.

**IDE-onderhoud landkaart (2026-05-23):** `lancedb_maintenance.py` + `LANCEDB_MAINTENANCE.bat`; merge snippet-preview; `audit_skill_drift.py`; volledige E2E `windows/audits/RUN_IDE_MAINTENANCE_E2E.bat` (rapport `IDE_MAINTENANCE_E2E_REPORT_*.md`).

**Institutioneel 10/10 (2026-05-23, afgerond + guardrails):** palet, NFR, normalizer-pariteit, score 10/10, labels verticaal, Web live palette. **Pipeline hardening (2026-05-27):** single-normalize contract (`prepare` → `render_institutional_from_prepared`), prose-coalesce + contextvars tabelpalet, `compact_institutional_check` PY↔TS, finalize-only streaming tests (`test_render_pipeline_contract.py`), score ANSI-cache, `bench_normalize_markdown.py`, E2E stap 2j parity. **Pseudo-tabel normalizer (2026-05-23):** … E2E 10/10 via `RUN_INSTITUTIONAL_E2E` stap **2h** (automatisch in `APPLY_INSTITUTIONAL_RUNTIME.bat`). **Context-aware pseudo-tabel (2026-05-25):** overview 2–6 kolommen (auxiliary grouped/collapsed), intent routing Python↔TS, CLI streaming eind-flush (`_prepare_stream_table_block`); ingeklapte **Component/Keuze/Status** + **Laag/Wat/Waarom** + em-dash → markdown-tabel (`_parse_collapsed_record_rows`, unheaded paragraphs onder `**Label:**`, eligibility, dedupe); SOUL: `### Veerkrachtstrategie` + tabel verplicht in `SOUL_SHARED_OUTPUT_FORMAT.md`; E2E **10/10** context + collapsed record; unit **51** tests. Na deploy: `SYNC_SOUL_SNIPPETS.bat` + Hermes-herstart + `/new`. **Herstel na IDE-drift:** `APPLY_INSTITUTIONAL_RUNTIME.bat` (config + SOUL + E2E 11/11). **Preventie:** `scripts/verify_institutional_guard.py`, drift in `diagnose_renderer.py --verify`, `.cursor/rules/institutional-presentatie.mdc`, `docs/INSTITUTIONAL_PORTING_GUIDE.md`. **Na pull/update/IDE:** `/new` + rooktest; na SOUL-wijziging: `SYNC_SOUL_SNIPPETS.bat`.

**TUI statusbalk-kosten (2026-05-24, rich bar + layout-fix):** Framework-default **`show_cost: true`** + **`cost_bar_mode: rich`**; altijd zichtbaar (`n/a`/`included`/`~NK tok`); `statusRuleColumns` (composer `paddingX` −2) + `resolveStatusRuleLayout`; live turn-kosten; Gemini 3.x → geschatte USD via `usage_pricing`; **`REBUILD_TUI.bat`** + volledige Hermes-herstart na TUI-pull (dist niet hot-reload). E2E `RUN_STATUS_BAR_COST_E2E.bat`.

**Klassieke CLI prompt-wachtrij (2026-05-25, PASS):** `/queue` list|pop|clear + `/q` alias; compact hint (max 2 previews, smalle terminal → `/queue list`); statusbalk `queue:N`; ack `[N] Queued for next turn|when idle`; review: hint geblokkeerd bij `_command_running`, `pop` via `get_nowait`, `format_removed_preview`. Module `hermes_cli/cli_pending_queue.py`. Unit **88** `test_cli_pending_queue.py`; E2E **17/17** `audits/RUN_CLI_PENDING_QUEUE_E2E.bat`. Docs: `windows/README.md`, `audits/README.md`.

**Klassieke CLI statusbalk-kosten (2026-05-24):** Pariteit met TUI — `hermes_cli/status_bar_cost.py` + dunne hooks in `cli.py` (`_append_status_bar_cost_fragments`, `/cost`); zelfde defaults en responsive tiers (≥52 cols session, ≥76 rich breakdown); data via `build_session_usage_snapshot` + `_seed_agent_session_cost`. **Layout (breed):** model → ctx → bar/% → duur → prompt-timer (`26s`, geen emoji) → kosten (gedimd blauw `status-bar-cost`) → breakdown → calls → tools (`0 tools` in full tier). **Tool-teller:** `agent.session_tool_executions` in `tool_executor.py`. **Gemini cache pricing:** `agent/usage_pricing.py` (`_GOOGLE_GEMINI_PRICING`, Standard tier; geen storage/Batch/Flex); geen `n/a` bij cache-hits op `provider=gemini`. E2E **`RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat`** (12/12 PASS).

**Statusbalk throughput tok/s (2026-05-25, PASS):** `hermes_cli/status_bar_throughput.py` + TUI `statusBarThroughput.ts`; segment **na** cost (`status-bar-tps`, gedimd wit); `display.show_status_bar_tps` default **aan**; `/tps`; gateway `config.get/set` (`status_bar_tps`/`tps`); agent stream timing (`record_agent_stream_delta`, `finalize_agent_call_tps`); CLI freeze overschrijft agent `_last_call_tps` niet. Unit: `test_status_bar_throughput.py`, cli `-k throughput`, `test_score_institutional_render.py` (renderer-score). E2E **14/14** `audits/RUN_STATUS_BAR_THROUGHPUT_E2E.bat` (incl. prompt-timer).

**Prompt-timer zonder emoji (2026-05-25, PASS):** `hermes_cli/status_bar_prompt_elapsed.py` (finite/negative guards); `display.show_prompt_timer_emoji` default **uit**; `/timer-emoji`; cli delegatie + `is_truthy_value`; verify `scripts/verify_fork_status_bar_display.py` na upstream-merge. Unit **72**; E2E **10/10** `audits/RUN_PROMPT_TIMER_DISPLAY_E2E.bat`. Team-default: `windows/team_display.defaults` `show_prompt_timer_emoji=false`.

**OpenRouter Pareto Code router (2026-05-24, PASS):** model-gated `min_coding_score` → `pareto-router` plugin op `openrouter/pareto-code`; verify `scripts/verify_pareto_router.py`; E2E `windows/audits/RUN_PARETO_E2E.bat` (8/8); `-IncludeParetoE2E` in `RUN_AUDITS.bat`. Geen live API-call in E2E.

**Codebase-audit smoke vs release (2026-05-24):** evidence-tiers E0–E3 in `docs/CODEBASE_AUDIT_EVIDENCE.md`; smoke-runner + E2E; `RUN_AUDITS -IncludeCodebaseSmoke`. Optioneel na pull/update: `-IncludeCodebaseSmoke` (~32s) of `-IncludeCodebaseSmokeE2E` via `Invoke-PostSyncCodebaseSmoke.ps1` (standaard uit). POST_GIT_PULL: verify via `.ps1` (geen pause). SOUL via anatomy; `/new` na SOUL-wijziging.

**Backup schema v3 (2026-05-23):** `backup_hermes.ps1` backupt `%LOCALAPPDATA%\hermes` → `runtime_hermes/`; legacy `~/.hermes` → `legacy_hermes/`; persona-subset → `localappdata_hermes/` (SOUL + `config.yaml`). Blokkeert als Hermes draait. Restore: `-RestoreRuntimeFull`, `-RestoreRuntimePersonas`, `-RestoreLegacyProfile`. Module: `windows/scripts/HermesBackupCommon.ps1`. Test: `windows/audits/RUN_BACKUP_E2E.bat`.

**Legal domein herstructurering** (2026-05): één RAG-bucket `legal`, rechtsgebied-**lenzen**, generieke `profiles\legal\SOUL.md`, zaak GCR in `LEGAL_ACTIVE_MATTERS.md`. Audit: `RUN_LEGAL_DOMAIN_E2E.bat`.

**Memory-trust automatisering (2026-05-29):** **`enforce_profile_memory_char_limits.ps1`** + **`Invoke-RepairProfileMemoryLimits`** (`-EnforceOnly` in `Invoke-MemoryTrustPostSync` vóór audit; `-MigrateOnly`/`-Full` in `SYNC_TRUST_RUNTIME` / `CONSOLIDATE_ROOT_MEMORIES.bat`). Backup trim: `%LOCALAPPDATA%\hermes\backups\memory-trim-*`. **`TrustRuntimeSync.psm1`:** stamp/drift; **`launch_trust_runtime_sync.ps1`:** stamp alleen bij schone audit, anders pending. **`deduplicate_memories.py`:** `HERMES_HOME`. SOUL governance ×→x (PS+Python); env-sync `Get-HermesAuditPython`. E2E: **`audits/RUN_MEMORY_REPAIR_TRUST_E2E.bat` (12/12)**; unit: `TrustRuntimeSync.Unit.Tests.ps1` + pytest `test_trust_runtime_sync.py`. FULL_VERIFY: UTF-8 logs, integration timeout 600s.

**Memory L1–L4 productieniveau (2026-05-25):** vault = `Documents/Hermes Knowledge`; geen L3. **`SYNC_TRUST_RUNTIME.bat`** = dedup + scrub + enforce + audit + production gate + `/new`. Zie ook blok hierboven (2026-05-29). E2E: `RUN_MEMORY_TRUST_INTEGRATION_E2E` (**10/10**), `RUN_PENDING_TRUST_START_E2E`, `RUN_MEMORY_IDENTITY_REPAIR_E2E`. **TUI auto `/new`**. Docs: `MEMORY_ARCHITECTURE.md`, `TRUST_FORENSIC_PROTOCOL.md`.

**Trust & Forensic protocol** (2026-05-22): SOUL advisory + legal forensic-blok, memory-seed in **alle** profielen, identiteit **J.** (scrub excl. `lancedb/`). Dagelijks/na pull: `SYNC_TRUST_RUNTIME.bat` (incl. vault-env sync); volledig+scrub: `APPLY_TRUST_PROTOCOL.bat`. `POST_GIT_PULL.bat` en `UPDATE_HERMES` post-merge roepen trust runtime aan. Audits: `RUN_TRUST_FORENSIC_E2E.ps1`, `RUN_LEGAL_DOMAIN_E2E.ps1`. Na sync: **nieuwe chat** in profiel `legal`.

**Domein-toolsets** (2026-05): manifest `docs/domain_toolsets.yaml` → `SYNC_DOMAIN_TOOLSETS.bat` (ook UPDATE/POST_GIT_PULL/APPLY_INSTITUTIONAL -IncludeTrustRuntime). **Runtime provision:** `--create-missing` (map, config, SOUL-template + snippets; geen patch `profiles.py`). Audit: `RUN_TOOLSET_DOMAIN_E2E.ps1`, smoke `RUN_PROVISION_DOMAIN_E2E.bat`. Zie `docs/DOMAIN_TOOLSET_AUDIT.md`, `docs/DOMAIN_BLUEPRINT.md` stap 9–10.

**ICT-team uitbreiding** (2026-05-23): 4 nieuwe profielen toegevoegd — `ict`, `security`, `dev`, `data`. Elk met eigen SOUL, lenzen, toolset, RAG-mappen en governance. Security = apart profiel (geen lens) met impact na J.-goedkeuring. E2E audit PASS met alle 14 profielen (incl. creative).

**Creative profiel (2026-05-26):** 14e domein `creative` — manifest, `SOUL_CREATIVE_DOMAIN.md`, `docs/13_Creative/`, routing, `fork_creative_skills` (manim-video, hyperframes optional), terminal in toolset; zie `DOMAIN_BLUEPRINT.md`.

**SOUL Anatomy** (2026-05-23): 14 domeinprofielen (`domain_toolsets.yaml`); geen `analyst`-domein. Stamp `%LOCALAPPDATA%\hermes\soul_anatomy_deploy.stamp` via `launch_soul_anatomy_deploy.ps1` (start + `POST_GIT_PULL -Force`). Keten: bootstrap → soul deploy → institutional (display; SkipSoul indien net deployed). Snippet-sync: `Test-NativeCommandFailed` + expliciet `exit 0` op child-scripts; pad-literals `/` in PS1; IDE-safe logging (geen `[TAG]` in double quotes). Audits: `RUN_SOUL_ANATOMY_E2E`, `RUN_SOUL_DEPLOY_START_E2E`. Na sync: `/new`.

**SOUL governance** (2026-05-23): shared snippets — `Zekerheid: NN%`, gaps bij elke strategie, fluff-definitie, geen multi-domein-compromis, tool max 1× retry, dossier 1/N wacht op "ga door", MC max 1 zin/optie. Root fallback: `SOUL_ROOT_FALLBACK.md` + `sync_root_soul_fallback.ps1` (ook na `SYNC_SOUL_SNIPPETS.bat`). Validatie: `validate_soul_anatomy.py --check-governance`. Doc: `docs/SOUL_GOVERNANCE.md`.

**P0+P1 afgerond**; Windows institutioneel: conda `hermes-env`, WT/skin, API-env sync. Open: bronnen in 7 lege `raw_source_files`-mappen (legal bronnen + submappen actief).

## Dev vs. install-clone

- **Dev:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`
- **Config:** `%USERPROFILE%\data\domains.yaml` — **14 domeinen** (incl. `creative` / `13_Creative`); voorbeeld `docs/domains.yaml.example`
- **User-data docs:** `%USERPROFILE%\data\STATUS.md`, `RECOVERY.md`; Kanban: `profiles\core\KANBAN_WORKFLOWS.md` — sync met `docs/USER_DATA_OPERATIONS.md`

## Documentatie (centraal)

| Doel | Bestand |
|------|---------|
| **Index** | `docs/README.md` |
| User-data sync | `docs/USER_DATA_OPERATIONS.md` |
| Model alle profielen | `docs/PROFILE_MODEL_INHERITANCE.md` |
| SOUL per profiel | `docs/PROFILE_SOUL.md` |
| SOUL governance | `docs/SOUL_GOVERNANCE.md` |
| SOUL anatomy | `docs/SOUL_ANATOMY_SPEC.md`, `docs/templates/SOUL_ANATOMY_BASE.md` |
| Domein-toolsets | `docs/DOMAIN_TOOLSET_AUDIT.md`, `docs/domain_toolsets.yaml` |
| Core routing / orchestrator | `docs/ORCHESTRATOR_ROUTING.md` |
| Legal architectuur / taxonomie | `docs/LEGAL_DOMAIN_ARCHITECTURE.md`, `docs/LEGAL_TAXONOMY.md` |
| Workspace / repo-hygiene | `docs/WORKSPACE_CONVENTIONS.md`, `windows/scripts/guard_git_clean.ps1` |
| Legal fork-skills + pytest | `skills/legal/`, `tests/skills/test_*_skill.py` |
| Repo-hygiene E2E | `audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat` (14/14); pytest `tests/windows/test_repo_hygiene_institutional_e2e.py` (`-m e2e`) |
| Landkaart (volledige lijsten) | skill `landkaart`, `/landkaart` |
| RAG twee fasen | `docs/RAG_TWEE_FASEN.md` |
| Presentatie (kleur + structuur) | `docs/INSTITUTIONAL_PRESENTATION.md`, `docs/INSTITUTIONAL_PORTING_GUIDE.md` |
| Rooktest renderer (10/10) | `docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md` |
| Trust & Forensic | `docs/TRUST_FORENSIC_PROTOCOL.md` |
| Memory L1–L4 (vault, geen L3) | `docs/MEMORY_ARCHITECTURE.md`, `docs/templates/MEMORY_ENV_VAULT.example` |
| E2E memory-architectuur | `windows/audits/RUN_MEMORY_ARCHITECTURE_E2E.bat` |
| E2E statusbalk-kosten (TUI) | `windows/audits/RUN_STATUS_BAR_COST_E2E.bat` · `-ApplyDisplayFix` · `RUN_AUDITS.bat -IncludeStatusBarCostE2E` |
| E2E statusbalk-kosten (klassieke CLI) | `windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat` · `RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E` |
| E2E statusbalk throughput (tok/s) | `audits/RUN_STATUS_BAR_THROUGHPUT_E2E.bat` (11/11); unit `tests/hermes_cli/test_status_bar_throughput.py` |
| Score renderer unit tests | `pytest tests/scripts/test_score_institutional_render.py` (rooktest-checklist) |
| Codebase-audit smoke (E1/E2) | `RUN_CODEBASE_SMOKE_E2E.bat` (E2E) · `RUN_CODEBASE_SMOKE_AUDIT.bat` (snel) · `RUN_AUDITS -IncludeCodebaseSmokeE2E` / `-IncludeAllE2E` · [CODEBASE_AUDIT_EVIDENCE.md](docs/CODEBASE_AUDIT_EVIDENCE.md) |
| E2E institutioneel | `windows/audits/RUN_INSTITUTIONAL_E2E.bat` |
| E2E context-aware pseudo-tabel | `windows/audits/RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.bat` |
| E2E collapsed record pseudo-tabel | `audits/RUN_COLLAPSED_RECORD_PSEUDO_TABLE_E2E.bat` (10/10); unit `tests/hermes_cli/test_collapsed_record_pseudo_table.py` |
| E2E klassieke CLI prompt-wachtrij | `audits/RUN_CLI_PENDING_QUEUE_E2E.bat` (17/17); unit `tests/hermes_cli/test_cli_pending_queue.py` (88) |
| Hermes start (bat) | `../../HERMES_START.md` |
| E2E Hermes split-home | `windows/audits/RUN_HERMES_HOME_E2E.bat` |
| E2E root inheritance | `windows/audits/RUN_ROOT_CONFIG_INHERITANCE_E2E.bat` |
| Windows | `windows/README.md` |
| Terminal / display / API-home | `windows/TERMINAL_WINDOWS.md` |
| Nous upstream | `windows/UPSTREAM_SYNC.md`; merge: `MERGE_UPSTREAM.bat`; audit: `windows/audits/UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md` |
| Voortgang | `memory-bank/progress.md` |

## Periodiek IDE-onderhoud (handmatig)

**Alle commando's (één doc):** `docs/IDE_MAINTENANCE.md` — snel: list, inspect, init-missing, `RUN_IDE_MAINTENANCE_E2E -ApplyDisplayFix -SkipMergePreview`; statusbalk TUI: `RUN_STATUS_BAR_COST_E2E.bat` / `-ApplyDisplayFix` / `RUN_AUDITS -IncludeStatusBarCostE2E`; statusbalk klassieke CLI: `RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat` / `RUN_AUDITS -IncludeClassicCliStatusBarCostE2E`; periodiek: verify, merge preview, skill drift, institutioneel E2E.

**Kernbestanden:** `windows/merge_upstream_fork.ps1` (merge + git-diff snippets), `windows/WindowsLocalAssetsManifest.ps1` (manifest sync/verify-keten).

## Volgende stappen (volgorde)

1. **Bronnen:** vul lege mappen onder `%USERPROFILE%\data\raw_source_files\` (01–03, 05–08, 09–12) — LanceDB-paden bestaan; echte kennis via `update_knowledge.bat`
2. **Ingest:** `windows\scripts\institutional_p0_p1.bat --ingest-remaining`
3. **MCP:** `update_knowledge.bat --mcp-test` (na ingest)
4. **Taakbalk (eenmalig):** oude pin los → `.lnk` uit `windows\` opnieuw vastmaken; Verkenner **F5**
5. **Setup:** `SETUP_HERMES.bat` (wizard) of `--files-only` / `OPEN_SETUP.bat`
6. **Python:** bij rode RAG/pip-fouten → `windows\REPAIR_PYTHON.bat` (geen handmatig `rmdir .venv`)

## Taakbalk (institutioneel)

| Script | Rol |
|--------|-----|
| `UPDATE_HERMES.bat` | Update + post-merge (trust, toolsets, **institutional runtime**, RAG, verify) |
| `SYNC_SOUL_SNIPPETS.bat` | Interaction + Output + Tool governance (`SOUL_SHARED_*.md`) |
| `SYNC_DOMAIN_TOOLSETS.bat` | Manifest → `platform_toolsets.cli` (root + profielen) |
| `MANAGE_BACKUPS.bat` | Inclusief `backup_soul_profiles` → `localappdata_hermes/` in backup |
| `POST_GIT_PULL.bat` | Na pull: trust + SOUL stamp-deploy + toolsets |
| `launch_soul_anatomy_deploy.ps1` | Stamp SOUL bij start / POST_GIT_PULL |
| `FIX_TASKBAR_ICONS.bat` | Handmatig icoon + pins |
| `.lnk` vastmaken | Sleep `.lnk` uit `windows\`, niet `.bat` |
| `SETUP_HERMES.bat` | Standaard bestanden + wizard; `--files-only` = geen wizard |

Iconen: goud = start/RAG, groen = setup, wit = update, roze = backup, cyaan = restore. Setup bewerken: alleen `scripts/windows/setup_hermes_windows.ps1` (niet volledige kopie naar `windows/`).
