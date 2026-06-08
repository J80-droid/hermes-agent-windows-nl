# Active context

## Focus

**Tier A drift + overlay pytest gate + CI (2026-06-08):** `pyproject.toml` op fork-intentional allowlist (ty gate + setuptools cap); catch-up `gateway/run.py` + `tools/todo_tool.py`; drift gate lokaal **0 must-upstream**. Overlay Tier B-patches voor 35 gemigreerde tests (`217d9e574`); upstream-pariteit `tests/hermes_cli` + CI-workflow (TUI vóór institutional E2E, `HERMES_AUDIT_PYTHON`, `HermesNousDrift` scope-fix). Fork pytest gate lokaal **854 passed**; CI `27110566360` bereikte institutional E2E — faalde op post-vitest drift (`appChrome.tsx`/`usage.ts`); fix: `Restore-HermesUiTuiTierASrc` in `Invoke-HermesUiTuiVitest`. Hardening H1–H14 + platform gate nog verifiëren na push; upstream ~496 commits achter — periodiek `UPDATE_HERMES.bat -Yes`.

**Ty fork gate + setuptools cap (2026-06-08):** `pyproject.toml` `[tool.ty.src]` = overlay + fork scripts/tests (geen volledige upstream ~10k diagnostics/panics); `windows/tests/RUN_TY_FORK_GATE.bat` exit 0; `setuptools>=77,<82` in `[dev]` + `guard_forbidden_packages.py` (torch 2.12+ metadata); docs `RAG_INSTITUTIONAL_ENV.md` § setuptools.

**Pytest fork gate + productie-poort (2026-06-07):** Runner-hardening: `Get-HermesPytestArgsFromConfig`, hashtable-splat `ExtraArgs`, stderr-`Continue`, `$global:LASTEXITCODE` na Tee; E2E `RUN_PYTEST_RUNNER_HARDENING_E2E.bat` (10/10). Drift-export split fork-intentional vs must-upstream. PSSA 0.

**Pad 1 SYNC_NOUS + lean overlay (2026-06-06):** Upstream merge ~199 commits (`d4f196072`); Tier A drift **0** (`Test-NousTreeIdentical` PASS). Toolset dashboard volledig upstream Tier A (`ToolsetConfigDrawer`, `web_server` env/post-setup routes, `main.py post-setup`). Overlay opgeschoond: verwijderd `web_server_fork_patch`, overlay web toolset-duplicaten; `tools_config_fork_patch` alleen MCP-sentinel + `_user_customized`; `argparse_fork_patch` alleen `config get` + profile flags. E2E: `RUN_TOOLSET_DASHBOARD_E2E` 9/9, `RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E` PASS, fork gates 8/8. Open P3: bronmappen `raw_source_files` handmatig vullen.

**PSSA 0 + CI vitest hardening (2026-06-06):** PSScriptAnalyzer 0 Warning/Error + `-FailOnWarning` in `RUN_AUDITS`/`RUN_PSScriptAnalyzer`; 9 gecommitte baseline-rapporten verwijderd; `windows/scripts/clean_audit_reports.ps1` voor lokale `*REPORT*`/`E2E_LOG`; gedeelde `HermesUiTuiNpm.ps1` (`Invoke-HermesUiTuiNpmEnsure`, `Invoke-HermesUiTuiVitest`) voor E2E + `rebuild_tui.ps1`; CI `fork-windows-institutional.yml`: Node 20 + `ui-tui npm ci`. Commits `26e107b56`, `20167641a` + follow-up vitest-fix.

**Nous overlay scorecard 10/10 (2026-06-02):** Tier A zuiver (`pyproject.toml` = upstream `signal`); pytest Windows via `Invoke-HermesAuditPytest`/`RUN_PYTEST.ps1`; `Invoke-HermesTierAPostAuditClean` (preflight/pre-overlay/postflight); UI `git clean` na build; RAG `fixtures/rag_minimal` + seed/E2E; CI upstream-remote + 14-fixes/pytest-audit-env/tier-a-cli guard; nightly `fork-windows-audits-nightly.yml`. Postflight: **geen** `git reset --hard` — gebruik `Invoke-HermesTierAPostAuditClean`.

**Chat rooktest 401 + auth BOM (2026-06-06, productie OK):** `runtime_provider` + overlay `load_config`-rebind; BOM-tolerante `_load_auth_store` + `repair_auth_json_bom.py`; rooktest via `run_hermes_cli_with_overlay.py` met MCP-server toolsets (`expand_cli_toolset_arg`); `doctor --fix` roept `repair_all_auth_json_bom()` + profile global-blocks strip aan. Commits `18fc71f22`–`38afeeb01` op `origin/main`. Verificatie: `institutional_p0_p1.bat` **PASS** (stap 4 search + Venice); `call hermes_legal_rooktest.bat "%HERMES_REPO%" "%PY%"` (setlocal-safe CLI-args). E2E: `RUN_INSTITUTIONAL_P0P1_WIRING_E2E` 15/15.

**Technische schuld + open poorten (2026-06-06):** `RUN_INSTITUTIONAL_PRODUCTION_GATE` **PASS** (pytest `PYTEST_ADDOPTS`/timeout-fix in `HermesShellCommon` + audit-scripts); `RUN_PLATFORM_HARDENING_PRODUCTION_GATE` PASS; RAG P0+P1 `--ingest-remaining` exit 0 (lege bronmappen = WARN, geen FAIL); CI platform gate + pre-commit `-Strict` + `python -m ruff` in `RUN_AUDITS`.

**Nous overlay afwerking (2026-06-06):** Plan uitgevoerd. **`RUN_AUDITS -IncludeAllE2E` PASS** (`windows/audits/RUN_AUDITS_plan_final3.log`). Tier A restore; fork gates in audit; dedup regel-§; trust preflight in RUN_AUDITS; overlay `usage.ts` + vitest copy `-Force`; bootstrap laadt `filesystem_sandbox`/`hardware_backend`/`config_snapshot`. `SYNC_TRUST_RUNTIME.bat` groen met SOUL+memory retry. RAG F6 uitgesteld (geen bronmappen).

**Profielwissel Windows structureel (2026-05-30, productie OK):** `/profile use` in WT — TUI-modal op achtergrondthread (`_schedule_profile_command_async`); sync/gateway/relaunch na TUI-exit; geen stderr-spinner tijdens `chat` relaunch (prompt `legal ❯`); audit `docs/PROFILE_SWITCH_WINDOWS_AUDIT.md`; E2E `RUN_PROFILE_SWITCH_E2E.bat` + pytest 29 passed.

**Legal memory taal-lagen 100% (2026-05-30):** EN trust + 3× NL legal USER-seed; SOUL § USER.md precedence; `RUN_LEGAL_MEMORY_LANGUAGE_LAYERS_E2E.bat` (9 stappen); pytest `test_legal_memory_language_layers.py` + `test_legal_memory_language_layers_e2e_harness.py` (38); `Get-HermesMemorySeedEntries` retourneert altijd `@()`-array.

**Legal proactive E2E geautomatiseerd (2026-05-30):** `Invoke-LegalProactiveSparringE2E.ps1` gekoppeld aan `APPLY_SOUL_ANATOMY_RUNTIME`, `launch_soul_anatomy_deploy`, `SYNC_TRUST_RUNTIME`, `RUN_AUDITS -IncludeLegalDomainE2E`; skip `HERMES_SKIP_LEGAL_PROACTIVE_E2E=1` / trust `HERMES_LEGAL_PROACTIVE_E2E_ON_TRUST=0`; core.ps1 Identity-insert check via regex (geen false positive op commentaar).

**Legal productie P0–P3 (2026-05-30):** `/legal-architectuur` + `legal_architecture_brief.py`; `VERIFY_LEGAL_RUNTIME.bat` (domains.yaml + parity) + `verify_legal_lens_parity.py` (`--fix`, diff bij mismatch); `ensure_legal_active_matters.ps1`; repo-E2E `audits/RUN_LEGAL_PRODUCTION_E2E.bat` (17 stappen) + runtime `RUN_LEGAL_DOMAIN_E2E` (12); unit tests harness/parity/brief/lens_from_path/score_renderer; `LEGAL_PRODUCTION_GATE.md`; ephemeral legal-paden (`_safe_path_for_prompt`, sticky profiel via `get_active_profile`); fase 2b.1 `legal_lens_from_path.py`; `SHOW_LEGAL_INGEST_DASHBOARD.bat`; renderer-testprompt disclaimer vs legal team.

**Legal P2+P4 geautomatiseerd (2026-05-30):** `LEGAL_TAXONOMY.md` in soul-deploy watch; `sync_legal_lens_from_taxonomy.ps1 --all` in `sync_all_domain_souls`; core+legal SOUL meta-routing (lenzen vs framework-team); `SYNC_LEGAL_LENS_FROM_TAXONOMY.bat`.

**Plan v2 fork 100% groen (2026-05-30):** `ee90ccb8c` op `origin/main` (Repair-CursorMcpConfig pad-literals, dashboard D7). Formele poort: `SYNC_TRUST_RUNTIME.bat` + `RUN_AUDITS -IncludeAllE2E` **PASS** — log `audits/RUN_AUDITS_closure_2026-05-30.log`. v2-acceptatie = fork/institutioneel, **niet** parallel ~29k upstream op Windows.

**RUN_AUDITS E2E-keten (2026-05-29, `74ae0f4e6`+):** Gateway cost/tps; CLI `config get` + profile switch; SOUL repair; Memory Repair Trust `Initialize-*`; `soul-runtime-prep` vóór E2E. Zie ook `windows/audits/RUN_AUDITS_LAST_RUN.log`.

**Codebase Viz pygount pre-warm + disk-cache (2026-05-29):** `scripts/warm_codebase_viz_pygount_cache.py` + `Initialize-CodebaseVizPygountCache` vóór dashboard; skip `backups/` + `.venv.disabled*`; disk-cache met git-HEAD-validatie + atomic write; E2E **`RUN_CODEBASE_VIZ_PYGOUNT_CACHE_E2E.bat` (8/8)**; defaults 600s/3600s/300s; skip: `HERMES_CODEBASE_VIZ_PREGOUNT_CACHE=skip`.

**Codebase Viz memory_pressure-fix (2026-05-30):** background refresh gebruikt git HEAD i.p.v. bestands-handtekening (geen valse cache-wipe); hydrate + memory guard serveert stale schijfcache bij revisie-mismatch; `/health` → `disk_cache`; docs `docs/CODEBASE_VIZ_TROUBLESHOOTING.md`; repair `windows\FIX_CODEBASE_VIZ_CACHE.bat` (cmd echo-fix); pytest codebase-viz plugin **87** passed.

**Institutionele hardening — productieniveau (2026-05-26, PASS):** `RepoHygieneCommon.ps1`; guard + QuickFix + health check; `UPDATE_HERMES.bat` / `POST_GIT_PULL.bat -QuickFix` (HERMES_WIN shift-safe); guard-log met trim; legal skills (rate limit, 2MB cap, ECLI); pytest **101** + `test_repo_hygiene_institutional_e2e.py`; E2E **14/14**; `RUN_AUDITS` vlaggen (`-IncludeInstitutionalHardeningE2E`, `-IncludeRepoHygieneE2E`, `-IncludeUpdateHermesIntegrationE2E`); CI `fork-windows-institutional.yml`; pre-commit warn-only; productie-poort **PASS**. **Cheat sheet:** `docs/INSTITUTIONAL_OPERATIONS.md#handige-commandos-fork` (canonical; gekoppeld vanuit README, AGENTS, windows/README, docs/README, repo-hygiene.mdc).

**Performance-architectuur RAG + runtime (2026-05-25, PASS):** LanceDB via `KnowledgeRepository.session()` (schema_migrate, bootstrap); enkelvoudige `collect_indexed_files`; `ingest_chunking` + `document_converter`; MCP `_ensure_mcp_knowledge`; batched orphan cleanup; `config_snapshot` + gateway/sandbox mtime-cache; `review_snapshot` (`HERMES_BG_REVIEW_MAX_MESSAGES`); Whisper-cache; `process_registry` pipe-close + Windows PTY fixes (`_pty_spawn_argv`, winpty str-write, detached taskkill, PTY reconcile); mcp stderr-log close. Unit tests RAG +83; `test_process_registry` 60 passed / 6 skipped (Windows). E2E **10/10** `RUN_PERFORMANCE_ARCHITECTURE_E2E.bat` (pytest incl. process_registry). Gate-rapporten `*_PRODUCTION_GATE_REPORT_*.md` gitignored. Refactor: `ingest_handlers`, `bootstrap_ingest_state`, `ingest._plan_incremental_ingest`.

**Platform hardening 10/10 (2026-05-25):** VectorStore-laag (`vector_store_*`, `lancedb_backend`), `KnowledgeRepository` (47 unit tests), regression E2E **10/10**, dedicated `RUN_KNOWLEDGE_REPOSITORY_E2E.bat` **8/8**, productie-poort `RUN_PLATFORM_HARDENING_PRODUCTION_GATE.bat`. Sandbox env-cache bust; hardware `reset_hardware_backend_cache()`; `patch_tool` her-propageert `PermissionError`. Docs: `docs/WINDOWS_PLATFORM_HARDENING.md`.

**Bootstrap fast-path (2026-05-30):** `launch_bootstrap.json` (schema v1, pyproject SHA-256 + repo + python_exe); `Test-HermesLaunchBootstrapFastPath` + in-process quick verify; geen nested `powershell` voor ensure_*; legacy `rag-deps.json`/`.stamp` fallback; upgrade naar JSON bij eerste snelle start; uitzetten: `HERMES_SKIP_LAUNCH_BOOTSTRAP_FAST_PATH=1`.

**Python institutioneel review-fixes (2026-05-25):** bootstrap stamp alleen na succesvolle RAG-sync; `rag-deps.json` fast-path (`rag_extras_verified`); REPAIR non-interactive; `HERMES_CONDA_ROOT`; `Test-HermesPythonHasPip`/`Test-HermesRagExtrasInstalled` catch op ongeldige stub-`.exe`; regression E2E **9/9** harness (`RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E`); pytest `test_hermes_python_institutional.py`. Runbook: `docs/INSTITUTIONAL_OPERATIONS.md`.

**Split-home & root inheritance (2026-05-25, productie-niveau — AF):** `model` + `auxiliary` + `providers` overerving; Venice merge + env sync; save-guard + cache-bust; keten `APPLY_HERMES_HOME_MIGRATION.bat` (7 stappen); E2E **16/16** (`RUN_HERMES_HOME_E2E`, incl. Jatevo) + **10/10** (`RUN_ROOT_CONFIG_INHERITANCE_E2E`, harness + `py_compile` guard). Runbook: `docs/HERMES_HOME_WINDOWS.md`.

**Venice quota + modelkeuze (2026-06):** `agent/venice_usage.py` — `/vquota`, `/usage`, statusbalk `VN …` (scope `none`); `/usage` account (`include_extended=account`: usage + usage-analytics); `/vquota` full (+ rate_limits/log, traits, compatibility_mapping). **Picker:** `hermes_cli/venice_model_picker.py` — trait-filter + OpenAI-mapping in `hermes model` (setup) en Telegram `/model` (`vf:` callbacks vóór modellenlijst); typed `/model gpt-4o --provider venice` via `resolve_venice_model_for_switch` in `model_switch.py`. **Setup:** optionele `extra_body.venice_parameters` (web_search, character_slug) na modelkeuze. Tests: `tests/agent/test_venice_usage.py`, `tests/overlay/test_venice_model_picker.py`.

**Jatevo custom provider (2026-06-01):** named provider onder `providers.jatevo`; `hermes model` → key-stap; live `/v1/models`; base URL **`https://jatevo.ai/v1`**; **`/jquota`** + **`/usage`**: dagrequests `0/N`, **tokens today**, **cost today** (562 = requests/dag, geen $); statusbalk **`JV used/max`**; 429 → `/jquota`. **Model/auth coherence (2026-06):** `doctor --fix` → `auth_from_config`; root `auth.json` sync via `sync_root_active_provider`; profiel-doctor vergelijkt root auth i.p.v. profiel-`nous` stale.

**Model/provider coherentie (2026-05-25, productie-af + hardening):** `persist_model_runtime()` schrijft atomisch naar root + sync `auth.active_provider`; `detect_model_provider_incoherence` / `repair_model_provider_coherence`; doctor `--fix` (ook `strip_all_profile_global_blocks`); setup blokkeert skip bij split-brain; `windows\REPAIR_MODEL_PROVIDER.bat`; `POST_GIT_PULL.bat -AutoRepairModelProvider` (opt-in); `read_auth_json` / nous shared store UTF-8 BOM-safe; gateway `HERMES_STRICT_CONFIG_COHERENCE=1` (opt-in). E2E `RUN_MODEL_PROVIDER_COHERENCE_E2E.bat`; drift via `verify_hermes_config_drift.ps1`. **Operationeel na deploy:** Hermes/gateway herstart + `/new` op gebruikersmachine.
**Model-catalog startup hardening (2026-05-27, uitgebreid 2026-06-01):** `Test-HermesModelCatalogAvailability` gebruikt `model_default_passes_startup_catalog_guard` (live catalog, `:free`-suffixen, `validate_requested_model`-parity); opt-in `HERMES_AUTOREPAIR_MODEL_CATALOG=1`.
**Domein-toolsets mcp+kanban + persist (2026-06-01):** manifest `mcp`+`kanban`; `hermes tools` zet `platform_toolsets._user_customized.cli`; sync slaat aangepaste profielen over (`--force-manifest`); kanban-gating leest `platform_toolsets.cli`; MCP-sentinel in `model_tools`; meta-key `_user_customized` gefilterd uit toolset-lijsten; legal `workspace.root` → repo (docs `WORKSPACE_CONVENTIONS.md`).
**Windows WT titelbalk-muis overlay (2026-05-30, OPGELOST + geverifieerd):** `ExpandConsoleToWorkArea` niet meer in `WT_SESSION` (root cause onzichtbare conhost op minimize/close); `RestoreConsoleFromWorkAreaOverlay`, `Invoke-HermesFixMouseBlocked`, `FIX_MOUSE_BLOCKED.bat`/`RESET_TERMINAL.bat`; deferred dashboard `Start-HermesDashboardAfterChatDetached`; geen auto-browser (`HERMES_SKIP_DASHBOARD_BROWSER`, leeg `OPEN_PATH`); docs `windows/MOUSE_OVERLAY_FIX.md`. Zie `TERMINAL_WINDOWS.md`. **Lacunes 1–16 (docs/guards):** memory bank sync, `.cursorrules`, START/LAUNCH_PROFILES, pytest WT-guard, `RUN_WT_MOUSE_OVERLAY_E2E.bat`, Clear-Host in WT, README-FORK, workspace-conventies, doc-drift `docs/*`.

**Startup UX/flow polish (2026-05-27):** dubbele model-catalog FAIL op launcher-start voorkomen door `launch_institutional_runtime.ps1 -SkipConfigDrift` in `launch_hermes.bat`; dashboard deferred na chat; zie bovenstaand overlay-fix.

**Windows chat-startfix (2026-05-27):** `TERM=xterm-256color` verwijderd; `hermes_chat.cmd`; orchestrator + quick dashboard; banner-parser zonder `(?ms).*` (fix hang na config-pad); model-banner alleen in `run_hermes_prepare`; zie `TERMINAL_WINDOWS.md`.

**Windows snelkoppelingen (2026-05-28):** `Set-HermesStartShellShortcut` (WT + `start_hermes.bat`); bureaublad niet meer overschreven door logo-only launcher; `HERMES_ONDERHOUD.bat` + `hermes_onderhoud.bat` (cmd-parsefix `(exit %ERR%)`); docs `START.md` / README / `TERMINAL_WINDOWS.md`.

**Taakbalk alle rollen via WT (2026-05-27):** `Set-HermesShellShortcut` = `wt.exe` + `Get-HermesWtShortcutArgumentLine` (fix cmd-geneste quotes onder WT-default-terminal); `verify_hermes_shortcut_paths.ps1`; `UPDATE_HERMES.bat` preflight via `%~dp0upstream_sync.ps1`; upstream preflight `-Force` / `HERMES_UPSTREAM_AUTO_CONFIRM=1`.

**Launch-profielen (2026-05-28):** `windows/launch_profiles.ps1`; **standaard full**; `start_hermes_minimal.bat` voor snelle chat; CLI-vlaggen gefilterd vóór `hermes_cli`; docs `START.md` + `LAUNCH_PROFILES.md`.

**Post-pull automatisering (2026-05-28):** `start_hermes.bat` = **één entrypoint** — auto-pull alleen als achter tracking branch (`Test-HermesGitPullNeeded.ps1`); anders direct start. `--pull` / `--sync` / `--no-pull`; `PULL_HERMES.bat` = alias `--pull`. `POST_GIT_PULL.bat` (relaunch via `Invoke-HermesPostPullRelaunch.ps1` + WT, `-KeepPid`); trust pending bij FAIL; UPDATE post-merge zelfde relaunch; CLI `_apply_post_sync_new_chat_notice`. E2E **14/14** + unit **56** harness; `test_hermes_git_pull_needed.py`.

**Sessie-onderhoud (2026-05-28):** `launch_hermes.bat` → `launch_hermes.ps1` → `launch_pre_chat_orchestrator.ps1` (bootstrap in orchestrator; `-AllowFailure` dot-source); `HermesSessionMaintenance.ps1` + stamps `%LOCALAPPDATA%\hermes\stamps\`; start: shortcut/TUI/drift-warn/model-repair; POST PostPullTail (toolsets, LanceDB, TUI, pins, smart RAG); `post_pull_maintenance` stamp dedupe (~15 min, zelfde head); `--sync -SkipRelaunch` + `Clear-HermesUpdateCheckCache`; `Invoke-HermesModelCatalogAutoRepair` (-RepoRoot); E2E **14/14** `audits/RUN_SESSION_MAINTENANCE_E2E.bat`; unit `HermesSessionMaintenance.Unit.Tests.ps1` + pytest harness.

**Launch UI Sink (2026-05-29):** `HermesLaunchUi.ps1` + `launch_hermes.ps1` als PS-entry; enkelvoudige console-schrijver (EL `[2K`), capture naar log, rich visual in WT; vaste goudgele kop `Write-HermesLaunchPinnedHeader` (`[93m]` regels 1–2) tijdens spinner; bootstrap via orchestrator (geen `-SkipBootstrap` in bat); E2E **8/8** `audits/RUN_LAUNCH_UI_SINK_E2E.bat` (geen live muis/WT); zie `windows/TERMINAL_WINDOWS.md`.

**Persistente snelkoppelingen (2026-05-29, doc 2026-05-30):** `HermesPersistentShortcuts.ps1` + `Invoke-HermesShortcutSyncRepair` — drie lagen: `windows\` (git, dubbelklik), `%LOCALAPPDATA%\Hermes\shortcuts\` (catalogus), `%LOCALAPPDATA%\Hermes\taakbalk\` (**pin-bron**, korte namen). Eénmalig vastmaken vanuit `taakbalk\`; `Repair-HermesTaskbarPinsFromStableDir` in-place na update/start. Canonieke doc: `windows/TAAKBALK_PINS.md`; entrypoints `OPEN_HERMES_TAAKBALK_PINS.bat`, `FIX_TASKBAR_ICONS.bat`.

**Web UI clean codebase (2026-05-29):** `web/` — `npm run lint` + `npm run build` groen; React-hooks fixes (sidebar tooltips via `useTooltipAnchor`, drop-up via `useDropUpFixedStyle`); i18n/theme context gesplitst; Chat PTY-channel `resume-{sessionId}` (geen `:` t.o.v. `_VALID_CHANNEL_RE`); `apply_team_display_profiles.py` utils-import via `sys.path`; E2E **11/11** `audits/RUN_WEB_UI_CLEAN_E2E.bat`; docs `web/README.md`. **A11y/hints (zelfde dag):** listbox-structuur Theme/Language switcher; `lib/aria.ts`; CSS surface utilities (`index.css`); Edge Tools axe-hints (aria strings, geen header in listbox); pytest curses guardrails UTF-8 + clamped-color regex op Windows.

**Upstream sync fase 2 + TUI layout (2026-05-25):** `Invoke-UpstreamGitMergeIfBehind` (preflight fetch-dedup, `$upstreamRef`, rev-list exit guards); `pip install -e .` na merge vóór `hermes update`; TUI `statusRuleMinLeftWidth` + `leftWidth`; slash **`/cost`** + upstream **`/queue`**. E2E **8/8** Phase2 + **7/7** `RUN_HERMES_SHELL_COMMON_E2E` (PSES). **UPDATE 2026-05-25:** 15 commits merge (conflict `core.ts` opgelost), daarna 2 commits auto-merge + volledige keten OK. **PSES:** `HermesShellCommon` `INFO:`/`OK:` tags, `Format-HermesStepLabel`, `Test-PsesTokenizer` 12 scripts.

**IDE-onderhoud landkaart (2026-05-23):** `lancedb_maintenance.py` + `LANCEDB_MAINTENANCE.bat`; merge snippet-preview; `audit_skill_drift.py`; volledige E2E `windows/audits/RUN_IDE_MAINTENANCE_E2E.bat` (rapport `IDE_MAINTENANCE_E2E_REPORT_*.md`).

**Institutioneel 10/10 (2026-05-23, afgerond + guardrails):** palet, NFR, normalizer-pariteit, score 10/10, labels verticaal, Web live palette. **Pipeline hardening (2026-05-27):** single-normalize contract (`prepare` → `render_institutional_from_prepared`), prose-coalesce + contextvars tabelpalet, `compact_institutional_check` PY↔TS, finalize-only streaming tests (`test_render_pipeline_contract.py`), score ANSI-cache, `bench_normalize_markdown.py`, E2E stap 2j parity. **Pseudo-tabel normalizer (2026-05-23):** … E2E 10/10 via `RUN_INSTITUTIONAL_E2E` stap **2h** (automatisch in `APPLY_INSTITUTIONAL_RUNTIME.bat`). **Context-aware pseudo-tabel (2026-05-25):** overview 2–6 kolommen (auxiliary grouped/collapsed), intent routing Python↔TS, CLI streaming eind-flush (`_prepare_stream_table_block`); ingeklapte **Component/Keuze/Status** + **Laag/Wat/Waarom** + em-dash → markdown-tabel (`_parse_collapsed_record_rows`, unheaded paragraphs onder `**Label:**`, eligibility, dedupe); SOUL: `### Veerkrachtstrategie` + tabel verplicht in `SOUL_SHARED_OUTPUT_FORMAT.md`; E2E **10/10** context + collapsed record; unit **51** tests. Na deploy: `SYNC_SOUL_SNIPPETS.bat` + Hermes-herstart + `/new`. **Herstel na IDE-drift:** `APPLY_INSTITUTIONAL_RUNTIME.bat` (config + SOUL + E2E 11/11). **Preventie:** `scripts/verify_institutional_guard.py`, drift in `diagnose_renderer.py --verify`, `.cursor/rules/institutional-presentatie.mdc`, `docs/INSTITUTIONAL_PORTING_GUIDE.md`. **Na pull/update/IDE:** `/new` + rooktest; na SOUL-wijziging: `SYNC_SOUL_SNIPPETS.bat`.

**TUI statusbalk-kosten (2026-05-24, rich bar + layout-fix):** Framework-default **`show_cost: true`** + **`cost_bar_mode: rich`**; altijd zichtbaar (`n/a`/`included`/`~NK tok`); `statusRuleColumns` (composer `paddingX` −2) + `resolveStatusRuleLayout`; live turn-kosten; Gemini 3.x → geschatte USD via `usage_pricing`; **`REBUILD_TUI.bat`** + volledige Hermes-herstart na TUI-pull (dist niet hot-reload). E2E `RUN_STATUS_BAR_COST_E2E.bat`.

**Klassieke CLI prompt-wachtrij (2026-05-25, PASS):** `/queue` list|pop|clear + `/q` alias; compact hint (max 2 previews, smalle terminal → `/queue list`); statusbalk `queue:N`; ack `[N] Queued for next turn|when idle`; review: hint geblokkeerd bij `_command_running`, `pop` via `get_nowait`, `format_removed_preview`. Module `hermes_cli/cli_pending_queue.py`. Unit **88** `test_cli_pending_queue.py`; E2E **17/17** `audits/RUN_CLI_PENDING_QUEUE_E2E.bat`. Docs: `windows/README.md`, `audits/README.md`.

**Klassieke CLI statusbalk-kosten (2026-05-24):** Pariteit met TUI — `hermes_cli/status_bar_cost.py` + dunne hooks in `cli.py` (`_append_status_bar_cost_fragments`, `/cost`); zelfde defaults en responsive tiers (≥52 cols session, ≥76 rich breakdown); data via `build_session_usage_snapshot` + `_seed_agent_session_cost`. **Layout (breed):** model → ctx → bar/% → duur → prompt-timer (`26s`, geen emoji) → kosten (gedimd blauw `status-bar-cost`) → breakdown → calls → tools (`0 tools` in full tier). **Tool-teller:** `agent.session_tool_executions` in `tool_executor.py`. **Gemini cache pricing:** `agent/usage_pricing.py` (`_GOOGLE_GEMINI_PRICING`, Standard tier; geen storage/Batch/Flex); geen `n/a` bij cache-hits op `provider=gemini`. E2E **`RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat`** (12/12 PASS).

**Statusbalk throughput tok/s (overlay, PASS):** `overlay/hermes_cli/status_bar_throughput.py` + TUI `overlay/ui-tui/.../statusBarThroughput.ts`; via bootstrap + `cli_fork_patch` / `agent_throughput_fork_patch`; `/tps` in `cli_tps_command.py`; CLI `_stream_delta` wrap voor live tok/s. E2E **14/14** `audits/RUN_STATUS_BAR_THROUGHPUT_E2E.bat`.

**Prompt-timer zonder emoji (overlay, PASS):** `overlay/hermes_cli/status_bar_prompt_elapsed.py`; runtime patch op `HermesCLI._format_prompt_elapsed`; verify `scripts/verify_fork_status_bar_display.py` (overlay-paden). E2E **10/10** `audits/RUN_PROMPT_TIMER_DISPLAY_E2E.bat`. Team-default: `windows/team_display.defaults` `show_prompt_timer_emoji=false`.

**OpenRouter Pareto Code router (2026-05-24, PASS):** model-gated `min_coding_score` → `pareto-router` plugin op `openrouter/pareto-code`; verify `scripts/verify_pareto_router.py`; E2E `windows/audits/RUN_PARETO_E2E.bat` (8/8); `-IncludeParetoE2E` in `RUN_AUDITS.bat`. Geen live API-call in E2E.

**Codebase-audit smoke vs release (2026-05-24):** evidence-tiers E0–E3 in `docs/CODEBASE_AUDIT_EVIDENCE.md`; smoke-runner + E2E; `RUN_AUDITS -IncludeCodebaseSmoke`. Optioneel na pull/update: `-IncludeCodebaseSmoke` (~32s) of `-IncludeCodebaseSmokeE2E` via `Invoke-PostSyncCodebaseSmoke.ps1` (standaard uit). POST_GIT_PULL: verify via `.ps1` (geen pause). SOUL via anatomy; `/new` na SOUL-wijziging.

**Backup schema v3 (2026-05-23):** `backup_hermes.ps1` backupt `%LOCALAPPDATA%\hermes` → `runtime_hermes/`; legacy `~/.hermes` → `legacy_hermes/`; persona-subset → `localappdata_hermes/` (SOUL + `config.yaml`). Blokkeert als Hermes draait. Restore: `-RestoreRuntimeFull`, `-RestoreRuntimePersonas`, `-RestoreLegacyProfile`. Module: `windows/scripts/HermesBackupCommon.ps1`. Test: `windows/audits/RUN_BACKUP_E2E.bat`.

**Legal domein herstructurering** (2026-05): één RAG-bucket `legal`, rechtsgebied-**lenzen**, generieke `profiles\legal\SOUL.md`, zaak GCR in `LEGAL_ACTIVE_MATTERS.md`. Audit: `RUN_LEGAL_DOMAIN_E2E.bat`.

**Memory-trust automatisering (2026-05-29):** **`enforce_profile_memory_char_limits.ps1`** + **`Invoke-RepairProfileMemoryLimits`** (`-EnforceOnly` in `Invoke-MemoryTrustPostSync` vóór audit; `-MigrateOnly`/`-Full` in `SYNC_TRUST_RUNTIME` / `CONSOLIDATE_ROOT_MEMORIES.bat`). Backup trim: `%LOCALAPPDATA%\hermes\backups\memory-trim-*`. **`TrustRuntimeSync.psm1`:** stamp/drift; **`launch_trust_runtime_sync.ps1`:** stamp alleen bij schone audit, anders pending. **`deduplicate_memories.py`:** `HERMES_HOME`. SOUL governance ×→x (PS+Python); env-sync `Get-HermesAuditPython`. E2E: **`audits/RUN_MEMORY_REPAIR_TRUST_E2E.bat` (12/12)**; unit: `TrustRuntimeSync.Unit.Tests.ps1` + pytest `test_trust_runtime_sync.py`. FULL_VERIFY: UTF-8 logs, integration timeout 600s.

**Memory L1–L4 productieniveau (2026-05-25):** vault = `Documents/Hermes Knowledge`; geen L3. **`SYNC_TRUST_RUNTIME.bat`** = dedup + scrub + enforce + audit + production gate + `/new`. Zie ook blok hierboven (2026-05-29). E2E: `RUN_MEMORY_TRUST_INTEGRATION_E2E` (**10/10**), `RUN_PENDING_TRUST_START_E2E`, `RUN_MEMORY_IDENTITY_REPAIR_E2E`. **TUI auto `/new`**. Docs: `MEMORY_ARCHITECTURE.md`, `TRUST_FORENSIC_PROTOCOL.md`.

**Trust & Forensic protocol** (2026-05-22): SOUL advisory + legal forensic-blok, memory-seed in **alle** profielen, identiteit **J.** (scrub excl. `lancedb/`). Dagelijks/na pull: `SYNC_TRUST_RUNTIME.bat` (incl. vault-env sync); volledig+scrub: `APPLY_TRUST_PROTOCOL.bat`. `POST_GIT_PULL.bat` en `UPDATE_HERMES` post-merge roepen trust runtime aan. Audits: `RUN_TRUST_FORENSIC_E2E.ps1`, `RUN_LEGAL_DOMAIN_E2E.ps1`. Na sync: **nieuwe chat** in profiel `legal`.

**Domein-toolsets** (2026-05): manifest `docs/domain_toolsets.yaml` → `SYNC_DOMAIN_TOOLSETS.bat` (ook UPDATE/POST_GIT_PULL/APPLY_INSTITUTIONAL -IncludeTrustRuntime). **Runtime provision:** `--create-missing` (map, config, SOUL-template + snippets; geen patch `profiles.py`). Audit: `RUN_TOOLSET_DOMAIN_E2E.ps1`, smoke `RUN_PROVISION_DOMAIN_E2E.bat`. Zie `docs/DOMAIN_TOOLSET_AUDIT.md`, `docs/DOMAIN_BLUEPRINT.md` (Niveau A), `docs/INSTITUTIONAL_DOMAIN_PLAN.md` (Niveau B, legal-model).

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
| E2E statusbalk throughput (tok/s) | `audits/RUN_STATUS_BAR_THROUGHPUT_E2E.bat` (11/11); unit `tests/overlay/test_status_bar_throughput.py` |
| Score renderer unit tests | `pytest tests/scripts/test_score_institutional_render.py` (rooktest-checklist) |
| Codebase-audit smoke (E1/E2) | `RUN_CODEBASE_SMOKE_E2E.bat` (E2E) · `RUN_CODEBASE_SMOKE_AUDIT.bat` (snel) · `RUN_AUDITS -IncludeCodebaseSmokeE2E` / `-IncludeAllE2E` · [CODEBASE_AUDIT_EVIDENCE.md](docs/CODEBASE_AUDIT_EVIDENCE.md) |
| E2E institutioneel | `windows/audits/RUN_INSTITUTIONAL_E2E.bat` |
| E2E context-aware pseudo-tabel | `windows/audits/RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.bat` |
| E2E collapsed record pseudo-tabel | `audits/RUN_COLLAPSED_RECORD_PSEUDO_TABLE_E2E.bat` (10/10); unit `tests/overlay/test_collapsed_record_pseudo_table.py` |
| E2E klassieke CLI prompt-wachtrij | `audits/RUN_CLI_PENDING_QUEUE_E2E.bat` (17/17); unit `tests/overlay/test_cli_pending_queue.py` (88) |
| Hermes start (bat) | `../../HERMES_START.md` |
| E2E Hermes split-home | `windows/audits/RUN_HERMES_HOME_E2E.bat` |
| E2E root inheritance | `windows/audits/RUN_ROOT_CONFIG_INHERITANCE_E2E.bat` |
| Windows | `windows/README.md` |
| Terminal / display / API-home | `windows/TERMINAL_WINDOWS.md` |
| Nous upstream | `windows/UPSTREAM_SYNC.md`; merge: `MERGE_UPSTREAM.bat`; audit-rapport: `UPSTREAM_UPDATE_E2E_REPORT_*_*.md` (lokaal) |
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
| `FIX_TASKBAR_ICONS.bat` / `OPEN_HERMES_TAAKBALK_PINS.bat` | Icoon + pins; vastmaken uit `%LOCALAPPDATA%\Hermes\taakbalk\` — zie `windows/TAAKBALK_PINS.md` |
| Taakbalk (eenmalig) | Rechtsklik *Vastmaken* op `Hermes *.lnk` in `taakbalk\`; niet slepen uit `windows\`/`backups\`; geen `.bat` slepen |
| `SETUP_HERMES.bat` | Standaard bestanden + wizard; `--files-only` = geen wizard |

Iconen: goud = start/RAG, groen = setup, wit = update, roze = backup, cyaan = restore. Setup bewerken: alleen `scripts/windows/setup_hermes_windows.ps1` (niet volledige kopie naar `windows/`).
