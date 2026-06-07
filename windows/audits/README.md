# Windows audits (optioneel)

Deze map bevat de **fork** kwaliteitspoorten (geen 1:1 upstream-kloon).

**IDE-markeringen op audit-`.ps1`?** Rode strepen zijn vaak **PSES-tokenizer false positives** (runtime is meestal OK). Extra “PSES-workarounds” in code kunnen **meer** meldingen geven (cross-file dot-source). Verifieer met AST, niet alleen de Problems-lijst. Workspace: `powershell.scriptAnalysis.enable: false`, `powershell.project.enable: false`. Verifieer met:

```bat
windows\audits\VALIDATE_AUDIT_PS1_SYNTAX.bat
```

**Pad-conventie (verplicht voor nieuwe audits):** dot-source `HermesShellCommon.ps1` en gebruik altijd `Join-HermesRepoPath` + `Read-HermesRepoText` voor repo-paden (forward slashes). Geen `$rel -replace '/', '\'` of `Join-Path $repoRoot 'mixed\paths'`. Navigatie naar repo-root vanuit een audit-runner: `Join-Path $PSScriptRoot '..\..'`. Zie `docs/WINDOWS_PLATFORM_HARDENING.md` en `HermesShellCommon.ps1`. `check-windows-footguns.py` flagt legacy PS1-padpatronen onder `windows/`.

Parent workspace (buiten repo): `windows\APPLY_WORKSPACE_IDE_SETTINGS.bat` — zie `docs/WORKSPACE_IDE_SETUP.md`. Daarna in Cursor: Command Palette → `PowerShell: Restart Session` en `Developer: Reload Window`.

**PSES-valkuil:** de IDE-parser (niet de runtime) faalt soms op:
- paden met extensie in single quotes (`'README.md'`) → gebruik `"README.md"` of `'README' + '.md'`
- type-literals in strings (`'[rag]'`, `"[OK]"`) → gebruik `-join '[', 'rag', ']'` of string-concatenatie
- `-e` als los token in single quotes (`'pip install -e .'`) → zet `-e` in een variabele (`$pipEditableFlag = '-e'`)
- `upstream/main` in here-strings → spreekbaar herschrijven (`upstream main`) of variabele
- ongequote git-refs (`git merge upstream/main`) → PSES ziet `/` als deling; altijd `'upstream/main'` en `'HEAD..upstream/main'`
- `/` in **dubbele** aanhalingstekens (`"upstream/main"`, `"miniconda3/anaconda3"`) → zelfde tokenizer-bug; gebruik enkelvoudige quotes of concatenatie
- `[TAG]` in strings (`'[ERROR]'`, `"[OK]"`) → type-literal; gebruik `OK:` / `ERROR:` of `-join '[', 'OK', ']'`
- **`-ForegroundColor` als switch** op `Write-Host` of in parameters (`$ForegroundColor`) → PSES splitst `-Foreground` + `Color`; gebruik `Write-HermesTag` / `Write-HermesSection` (plain `Write-Host`, geen kleur-switches)
- **`function Set-*`** in `.psm1` met grote `param()`-blokken → tokenizer-cascade; prefer `Register-*` / `Write-*` voor stamps (bijv. `Register-PendingTrustRuntimeRequired`)

**IDE:** na wijzigingen: PowerShell: Restart Session + Developer: Reload Window. Verifieer met `windows\tests\Test-PsesTokenizer.ps1` (AST), `windows\tests\HermesShellCommon.Unit.Tests.ps1` (helpers), `RUN_HERMES_SHELL_COMMON_E2E.bat` (PSES-poort) en `VALIDATE_AUDIT_PS1_SYNTAX.bat`. Logging-tags in `HermesShellCommon.ps1` gebruiken `INFO ` / `OK ` (spatie, geen dubbele punt — PSES-tokenizer).

Runtime/AST: vertrouw op `VALIDATE_AUDIT_PS1_SYNTAX.bat`.

**Trust E2E:** `RUN_TRUST_FORENSIC_E2E.ps1` is alleen een launcher; logica staat in `TrustForensicE2E.core.ps1` (dot-source naar `HermesTrustForensicPatterns.ps1`, `HermesTrustForensicProfileChecks.ps1`, `MemoryAuditCommon.ps1`). BAT en `RUN_AUDITS` blijven de launcher aanroepen.

**Classic CLI statusbalk E2E:** `RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1` is alleen een launcher; logica staat in `ClassicCliStatusBarCostE2E.core.ps1` (geen dot-source — stabiel in IDE/PSES).

**Memory E2E:** `RUN_MEMORY_ARCHITECTURE_E2E.ps1` is alleen een launcher; logica staat in `MemoryArchitectureE2E.core.ps1` (dot-source naar `MemoryAuditCommon.ps1`). Geen dot-source in de launcher — stabiel in Cursor/PSES.

| Runner | Doel |
| ------ | ---- |
| **`RUN_CODEBASE_SMOKE_AUDIT.bat`** | Snelle smoke (E1/E2): pytest/verify-subset; rapport `CODEBASE_SMOKE_AUDIT_REPORT_*.md`. **Geen E3.** |
| **`RUN_CODEBASE_SMOKE_E2E.bat`** | E2E-poort (5 stappen): repo files + strict template + pytest wiring + smoke audit + rapport-check; `CODEBASE_SMOKE_E2E_REPORT_*.md` (gitignored) |
| **`POST_GIT_PULL.bat -IncludeCodebaseSmoke`** | Snelle smoke na pull (~32s; optioneel) |
| **`POST_GIT_PULL.bat -IncludeCodebaseSmokeE2E`** | E2E-poort na pull (~45s; optioneel) |
| **`UPDATE_HERMES.bat -IncludeCodebaseSmoke`** / **`-IncludeCodebaseSmokeE2E`** | Zelfde na upstream post-merge via `Invoke-PostSyncCodebaseSmoke.ps1` |
| **`RUN_AUDITS.bat -IncludeCodebaseSmoke`** | Alleen smoke-runner (sneller) |
| **`RUN_AUDITS.bat -IncludeCodebaseSmokeE2E`** | Volledige codebase-smoke E2E |
| **`RUN_AUDITS.bat -IncludeAllE2E`** | Inclusief codebase-smoke E2E (~30s extra) |
| **`RUN_AUDITS.bat`** | Gecombineerd: `verify_hermes_home`, PSScriptAnalyzer (SKIP indien ontbreekt), `check-windows-footguns.py`, ruff (SKIP), `pytest tests/overlay/`, pytest profiel-subset |
| **`RUN_AUDITS.bat -IncludeNousOverlayInstitutionalE2E`** | Nous overlay institutional E2E (`audits\RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E.bat`) |
| **`RUN_AUDITS.bat -IncludeStatusBarThroughputE2E`** | Throughput tok/s E2E (`audits\RUN_STATUS_BAR_THROUGHPUT_E2E.bat`) |
| **`RUN_AUDITS.bat -IncludePromptTimerDisplayE2E`** | Prompt-timer zonder emoji E2E (`audits\RUN_PROMPT_TIMER_DISPLAY_E2E.bat`) |
| **`RUN_AUDITS.bat -IncludeProfileE2E`** | Bovenstaande + profielwissel E2E |
| **`RUN_AUDITS.bat -IncludeInstitutionalE2E`** | Bovenstaande + landkaart/SOUL-backup/templates E2E |
| **`RUN_AUDITS.bat -IncludeRepoHygieneE2E`** | Repo-root guard/gitignore/skills (~10s): `audits\RUN_REPO_HYGIENE_E2E.bat` |
| **`audits\RUN_CREATIVE_DOMAIN_E2E.bat`** | Creative profiel (11/11): manifest, docs, SOUL, fork-skills, provision; unit `tests\audits\test_creative_domain_e2e_harness.py` |
| **`audits\RUN_DASHBOARD_ON_START_E2E.bat`** | Dashboard bij `launch_hermes` (7/7): `--no-open`, skip-env, unit tests |
| **`RUN_WT_MOUSE_OVERLAY_E2E.bat`** | WT titelbalk/muis: pytest overlay-contracten + handmatige checklist (geen live UI-automation) |
| **`RUN_AUDITS.bat -IncludeInstitutionalHardeningE2E`** | Geïntegreerde poort H1–H14 (~20s): QuickFix, legal pytest, preflight-log |
| **`RUN_AUDITS.bat -IncludeUpdateHermesIntegrationE2E`** | UPDATE/QuickFix wiring (~7s): `audits\RUN_UPDATE_HERMES_INTEGRATION_E2E.bat` (12/12) |
| **`RUN_AUDITS.bat -IncludeInstitutionalProductionGate`** | Zware poort (~2+ min): Python + platform + hardening 14/14 + wiring |
| **`RUN_AUDITS.bat -IncludeAllE2E`** | Institutioneel + legal + profiel + toolset + SOUL + memory + statusbalk + split-home + **hardening 14/14** + `nous-overlay-fork-gates-e2e` (niet `-IncludeInstitutionalProductionGate`). Preflight: `strip_profile_global_config_blocks.py` (overlay bootstrap). **Tier-A:** `Invoke-HermesTierAPostAuditClean` (preflight / pre-overlay / postflight); debug: `-SkipTierAPostClean`. |
| **`audits/RUN_RUN_AUDITS_14_FIXES_E2E.bat`** | Snelle regressie 14-fixes (10/10): thread-timeout, strip bootstrap, doctor `--fix`, audit pytest helpers, YOLO width (~2 min). |
| **`RUN_SOUL_DEPLOY_START_E2E.bat`** | Stamp/startketen: launch_hermes, POST_GIT_PULL, upstream SkipSoul, anatomy subset |
| **`RUN_MEMORY_IDENTITY_REPAIR_E2E.bat`** | Runtime identity scrub (pre-audit), post-sync integratie, skip-flag, unit + pytest (**PASS**) |
| **`RUN_MEMORY_TRUST_INTEGRATION_E2E.bat`** | Geïntegreerde poort: post-sync, pending trust, workspace template/apply, PSES AST, unit tests (**10 stappen**) |
| **`APPLY_WORKSPACE_IDE_SETTINGS.bat`** | Parent `Hermes_agent_WS\.vscode\settings.json` vanuit template (PSES uit); zie `docs/WORKSPACE_IDE_SETUP.md` |
| **`RUN_PENDING_TRUST_START_E2E.bat`** | Pending trust bij start: stamp, post-merge, launcher (skip/max/dry-run), pytest wiring |
| **`RUN_AUDITS.bat -IncludePendingTrustStartE2E`** | Zelfde pending-trust E2E in gecombineerde audit |
| **`RUN_AUDITS.bat -IncludeSoulDeployStartE2E`** | Alleen SOUL deploy-start E2E |
| **`RUN_AUDITS.bat -IncludeToolsetDomainE2E`** | `platform_toolsets.cli` per profiel vs manifest |
| **`RUN_AUDITS.bat -IncludeLegalDomainE2E`** | Legal unit (`LegalDomainE2E.Unit.Tests.ps1`) + volledige E2E (taxonomie, SOUL, submappen, rooktest) |
| **`APPLY_INSTITUTIONAL_RUNTIME.bat`** | Handmatig: display + SOUL + E2E (incl. 2h pseudo-tabel); **automatisch** na `UPDATE_HERMES.bat` (post-merge, `-SkipE2E`) |
| **`RUN_IDE_MAINTENANCE_E2E.bat`** | Volledige IDE-landkaart E2E (16 stappen, rapport `IDE_MAINTENANCE_E2E_REPORT_*.md`); `-Full` = display-fix + `RUN_INSTITUTIONAL_E2E`; `-SkipMergePreview` = zonder git fetch |
| **`RUN_AUDITS.bat -IncludeIdeMaintenanceE2E`** | Bovenstaande IDE-onderhoud E2E in gecombineerde poort |
| **`RUN_INSTITUTIONAL_E2E.bat`** | Audit (11 stappen incl. 2h pseudo-tabel + profiel-chat-UX); `-ApplyRuntime` = eerst runtime |
| **`RUN_INSTITUTIONAL_E2E.bat -ApplyRuntime`** | Zelfde als `APPLY_INSTITUTIONAL_RUNTIME.bat` (zonder dubbele E2E) |
| **`RUN_LEGAL_DOMAIN_E2E.bat`** | Legal lenzen, actieve zaken, bronlayout |
| **`RUN_TOOLSET_DOMAIN_E2E.bat`** | 6-stappen E2E: home verify, manifest, pytest, drift, tool-counts, SOUL governance |
| **`RUN_PROVISION_DOMAIN_E2E.bat`** | Smoke: `--create-missing` op tijdelijke HERMES_HOME (geen productie) |
| **`RUN_AUDITS.bat -IncludeProvisionDomainE2E`** | Alleen provision-smoke |
| **`RUN_AUDITS.bat -RequirePSScriptAnalyzer`** | PSSA verplicht (exit 1 als module ontbreekt) |
| **`windows\tests\RUN_PSScriptAnalyzer.bat`** | Volledige `windows\` lint (instellingen: `PSScriptAnalyzerSettings.psd1`) — verwacht **0 Warning/Error** |
| **`RUN_PROFILE_SWITCH_E2E.bat`** | Alleen profielwissel E2E |
| **`RUN_MEMORY_ARCHITECTURE_E2E.bat`** | L4 vault-paden, sync, geen L3, profiel-limits 4000/1800, **alle profielen** MEMORY/USER, dedup-keten, TUI auto `/new` (**16 stappen**) |
| **`RUN_MEMORY_PRODUCTION_GATE.bat`** | Gecombineerd: trust limits + memory E2E (18/18) + trust forensic E2E + pytest memory/trust |
| **`RUN_AUDITS.bat -IncludeMemoryProductionGate`** | Alleen memory productie-poort (ook in `-IncludeAllE2E`) |
| **`RUN_UPSTREAM_MERGE_INTEGRATION_E2E.bat`** | Na upstream-merge: `cwdReserve`+`statusRuleWidths`, profile create strip+s6, vitest/pytest/harness (**10 stappen**) |
| **`RUN_UPSTREAM_SYNC_PHASE2_E2E.bat`** | Fase-2 keten: `Invoke-UpstreamGitMergeIfBehind`, preflight fetch-dedup, `pip install -e .` na merge, TUI `leftWidth`/`statusRuleMinLeftWidth`, vitest + harness (**8 stappen**) |
| **`RUN_HERMES_SHELL_COMMON_E2E.bat`** | PSES-safe logging/git: `HermesShellCommon` API, `Format-HermesStepLabel`, geen `2>&1`/`[TAG]` in kritieke ps1, AST + python harness (**7 stappen**) |
| **`RUN_STATUS_BAR_COST_E2E.bat`** | TUI statusbalk (rich): `show_cost`, `cost_bar_mode`, breakdown, turn-delta, live `~$turn`, gateway smoke |
| **`RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat`** | Klassieke CLI (`hermes chat`): `status_bar_cost.py`, `cli.py` hooks, `/cost`, smoke + pytest |
| **`RUN_PARETO_E2E.bat`** | OpenRouter Pareto Code router: model-gate, transport/summary parity, pytest, verify script |
| **`RUN_PSEUDO_TABLE_NORMALIZER_E2E.bat`** | Pseudo-tabel normalizer: underscore/vs→markdown, pytest + TS parity + diagnose/score (10 stappen) |
| **`RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.bat`** | Context-aware overview (2-6 kolommen): grouped/collapsed auxiliary, Component/Keuze/Status em-dash, intent routing, TS parity (10 stappen) |
| **`..\audits\RUN_COLLAPSED_RECORD_PSEUDO_TABLE_E2E.bat`** | Dedicated collapsed-record parser: eligibility, pipe-escape, architectuur-probe, TS parity (10 stappen; harness in `audits/`) |
| **`RUN_WINDOWS_PLATFORM_HARDENING_E2E.bat`** | Platform hardening: filesystem sandbox, hardware backend (CUDA/DirectML/CPU), LanceDB storage lifecycle (10 stappen) |
| **`RUN_PLATFORM_HARDENING_REGRESSION_E2E.bat`** | Regressie: review-fixes, PS1 Join-HermesRepoPath, footguns PS1-regel (**10 stappen**) |
| **`RUN_PLATFORM_HARDENING_PRODUCTION_GATE.bat`** | Gecombineerd: beide platform E2E's + pytest subset + `footguns --all` |
| **`RUN_KNOWLEDGE_REPOSITORY_E2E.bat`** | KnowledgeRepository agent-API: edge cases, caller wiring, pytest (8 stappen) |
| **`RUN_PERFORMANCE_ARCHITECTURE_E2E.bat`** | Performance-architectuur: RAG lifecycle/scan/MCP, config-snapshot, harness (11 scenario's), pytest-subset (RAG performance tests + `test_process_registry.py` + sandbox/hardware/config/review); rapport `PERFORMANCE_ARCHITECTURE_E2E_REPORT_*.md` (gitignored) |
| **`RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.bat`** | Institutioneel Python: conda hermes-env, IDE sync, venv-quarantaine, pytest (8 stappen) |
| **`RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat`** | Regressie review-fixes: bootstrap fast-path (`launch_bootstrap.json`), RAG-manifest, in-process ensure, pytest (9 stappen harness) |
| **`RUN_INSTITUTIONAL_PRODUCTION_GATE.bat`** | Gecombineerd: Python E2E + KnowledgeRepository + platform gate + wiring-check |
| **`RUN_AUDITS.bat -IncludePseudoTableNormalizerE2E`** | Bovenstaande pseudo-tabel E2E in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeInstitutionalPipelineE2E`** | Institutional pipeline E2E (`audits/InstitutionalPipelineE2E.core.ps1`, 11 stappen) in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeMemoryArchitectureE2E`** | Bovenstaande memory E2E in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeStatusBarCostE2E`** | Bovenstaande statusbalk-kosten E2E in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E`** | Klassieke CLI statusbalk-kosten E2E in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeParetoE2E`** | Bovenstaande Pareto router E2E in gecombineerde poort |
| **`RUN_HERMES_HOME_E2E.bat`** | Split-home: repo-artefacten, pytest, drift, inventory, gateway, Venice, auxiliary inheritance (**14 stappen**) |
| **`RUN_ROOT_CONFIG_INHERITANCE_E2E.bat`** | Root inheritance: pytest + isolated harness (8 scenario's) + runtime Venice/auxiliary (**10 stappen**) |
| **`RUN_AUDITS.bat -IncludeHermesHomeE2E`** | Bovenstaande Hermes-home E2E in gecombineerde poort |
| **`APPLY_HERMES_HOME_MIGRATION.bat`** | Eenmalig: backup → deprecate → preset → Venice merge → strip → env sync → E2E |
| **`windows\tests\RUN_PYTEST.bat`** | Brede pytest (excl. integration) |
| **`windows\VERIFY_WINDOWS_CHAIN.bat`** | Script-keten backup/RAG (handmatig, pause) |
| **`RUN_BACKUP_E2E.bat`** | Lightweight backup schema v3 test (`tests/windows/test_backup_runtime.ps1`) |
| **`UPDATE_HERMES.bat`** | Zelfde verify via `verify_windows_script_chain.ps1` in keten (geen pause) |

## Legal domein E2E

```text
windows\audits\RUN_LEGAL_DOMAIN_E2E.bat
```

Stappen: repo taxonomie → runtime SOUL (geen GCR in Identity) → `LEGAL_ACTIVE_MATTERS.md` → submappen `04_Legal_Corporate` → taxonomy-sync dry-run → pytest → rooktest search.

Bron-migratie: `windows\scripts\MIGRATE_LEGAL_LAYOUT.bat -Apply` daarna `update_knowledge.bat legal`.

## Institutioneel E2E (landkaart + SOUL)

```text
windows\audits\RUN_INSTITUTIONAL_E2E.bat
```

Stappen: repo → pytest (landkaart, presentatie, **2d profiel-chat-UX**, **2e Rich renderer**, **2f diagnose**, **2g score**, **2h pseudo-tabel E2E**) → landkaart smoke → backup → SOUL Interaction/Outputformaat/**5c profielwissel-regel** → display alle profielen (incl. `assistant_render_style`, `assistant_palette`, `assistant_label_columns`) → rich_output → restore/update → **pytest profielwissel** → **SWITCH legal→core** → intent-smoke.

### Wat de institutioneel E2E **wel** dekt (sinds 11 stappen)

| Onderdeel | Stap |
| --------- | ---- |
| Natuurlijke taal → profielnaam (`cli._parse_profile_switch_intent`) | 2d, 11 |
| Prompt gebruikt sticky `active_profile` (niet verkeerd HERMES_HOME-pad) | 2d |
| SOUL Interaction: `/profile use`, geen advies “alleen buiten sessie” | 5c |
| Sticky wissel via `SWITCH_PROFILE.bat` + pytest profiel-subset | 9, 10 |

### Wat deze E2E **niet** deed (bewust of apart script)

| Gap | Waarom / waar |
| --- | ------------- |
| Gebruiker zegt in chat “schakel naar core” → **agent** antwoordt met `/profile use core` | Geen live LLM; model kan oude context hebben. Handmatig: nieuwe chat na SOUL-sync. |
| Prompt toont direct `core ❯` **na** natuurlijke taal in dezelfde lopende sessie | 2d test code/prompt-logica, geen terminal-herstart na intent-intercept. |
| Volledige profielwissel-E2E (alle varianten) | `windows\audits\RUN_PROFILE_SWITCH_E2E.bat` (`SWITCH_PROFILE.bat`, `test_profile_switch_e2e`, …). |
| SOUL Interaction-regels **in gedrag** na lange sessie | 5c leest alleen tekst op schijf; geen sessie met verouderde SOUL in context. |

**Handmatig na deploy:** `APPLY_INSTITUTIONAL_RUNTIME.bat` → Hermes herstarten → **nieuwe chat** → profielwissel via `/profile use <naam>` of natuurlijke zin (CLI voert wissel uit vóór het model).

Presentatie: zie `docs/INSTITUTIONAL_PRESENTATION.md`. **Eén commando:** `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` (of E2E met `-ApplyRuntime`). Display-check stap 6/11: **alle** profielen onder `profiles\`.

Rapport: `INSTITUTIONAL_E2E_REPORT_*_*.md` (lokaal/gitignored; log `INSTITUTIONAL_E2E_LAST_RUN.log` idem).  
Upstream + UPDATE audit: `UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md`.  
Memory L1–L4 audit: `MEMORY_ARCHITECTURE_E2E_REPORT_2026-05-23.md` (**16 stappen** sinds 2026-05-24; tijdelijke logs `MEMORY_ARCHITECTURE_E2E_REPORT_*_*.md` gitignored).  
Statusbalk-kosten audit: `STATUS_BAR_COST_E2E_REPORT_*.md` (10 stappen; `RUN_STATUS_BAR_COST_E2E.bat`).  
Klassieke CLI statusbalk-kosten: `CLASSIC_CLI_STATUS_BAR_COST_E2E_REPORT_*.md` (12 stappen incl. Gemini cache pricing; `RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat`).

## Context-aware pseudo-tabel E2E (overview 2-6 kolommen)

```text
windows\audits\RUN_CONTEXT_AWARE_PSEUDO_TABLE_E2E.bat
```

Dedicated audit naast `RUN_PSEUDO_TABLE_NORMALIZER_E2E.bat` (basis vs/underscore). Dekt de **contextafhankelijke** normalizer: auxiliary-overzichten (4 kolommen grouped/collapsed), 2-koloms config, intent routing, scheiding tussen groepen, CLI streaming eind-flush, TS parity overview-fixtures.

| Stap | Controle |
| ---- | -------- |
| 1–4 | Repo-artefacten, Python/TS overview parser + intent, CLI `_prepare_stream_table_block` |
| 5 | Isolated harness (8 scenario's): `ContextAwarePseudoTableE2E.harness.py` |
| 6–7 | pytest overview unit + TS parity `auxiliary_overview_4col` / `_2col` |
| 8–10 | `verify_pseudo_table_normalizer --verify`, diagnose overview-warning, SOUL/docs |
| 11–12 | `py_compile` + vs/Cloud-Lokaal regressie |

Rapport: `CONTEXT_AWARE_PSEUDO_TABLE_E2E_REPORT_*.md`.

## Collapsed record pseudo-tabel E2E

```text
audits\RUN_COLLAPSED_RECORD_PSEUDO_TABLE_E2E.bat
```

Dedicated audit voor ingeklapte `Component`/`Keuze`/`Status`-regels (em-dash op één regel, multi-line anchor-split, eligibility zodat `**Groep**`+Provider/Model auxiliary blijft). Zie ook `audits/README.md` (scenario-tabel E1–E10).

| Stap | Controle |
| ---- | -------- |
| 1–6 | Harness `CollapsedRecordPseudoTableE2E.harness.py` (em-dash, multi-line, Groep-guard, pipe-escape) |
| 7–8 | `verify_pseudo_table_normalizer.py` architectuur-probe; pytest `test_collapsed_record_pseudo_table.py` |
| 9–10 | Volledige pipeline + TS parity via `scripts/normalize_assistant_markdown_ts_runner.ts` |

Unit tests (los): `pytest tests/overlay/test_collapsed_record_pseudo_table.py` (48 scenario's, happy path + edge/negatief).

## Windows platform hardening E2E

```text
windows\audits\RUN_WINDOWS_PLATFORM_HARDENING_E2E.bat
```

Dedicated audit voor filesystem sandbox, hardware backend fallback en LanceDB storage lifecycle op Windows.

| Stap | Controle |
| ---- | -------- |
| 1/10 | Repo-artefacten (`filesystem_sandbox.py`, `hardware_backend.py`, `lancedb_storage.py`, tests, runners) |
| 2/10 | Filesystem sandbox wiring via `overlay/tools/file_tools_fork_patch.py` |
| 3/10 | Hardware backend + CLI startup logging (`log_local_inference_backends`) |
| 4/10 | LanceDB lifecycle wiring (`mcp_server`, `ingest`, preflight, shutdown hooks) |
| 5/10 | Config `workspace.enforce_sandbox` + `pyproject.toml` extra `voice-windows` |
| 6/10 | Isolated harness (`WindowsPlatformHardeningE2E.harness.py`, 12 scenario's) |
| 7–9/10 | pytest: `test_file_tools_fork_patch`, `test_filesystem_sandbox`, `test_hardware_backend`, `test_lancedb_storage` |
| 10/10 | `check-windows-footguns.py` op gewijzigde modules |

Optioneel: `-SkipPytest` op `RUN_WINDOWS_PLATFORM_HARDENING_E2E.ps1`.

Rapport: `WINDOWS_PLATFORM_HARDENING_E2E_REPORT_*.md`. Zie `docs/WINDOWS_PLATFORM_HARDENING.md`.

## Platform hardening regressie E2E

```text
windows\audits\RUN_PLATFORM_HARDENING_REGRESSION_E2E.bat
```

Validatie van code-review fixes en PS1-padmigratie (naast de basis hardening E2E).

| Stap | Controle |
| ---- | -------- |
| 1/10 | Repo-artefacten (review modules + regression runners) |
| 2/10 | Geen legacy `$rel -replace` in `windows/audits/*.ps1` |
| 3/10 | `HermesShellCommon.ps1` pad-conventie gedocumenteerd |
| 4/10 | `check-windows-footguns.py` PS1-padregel actief |
| 5/10 | Code wiring: env-var sandbox, GPU fallback, lifecycle shutdown, DI-laag |
| 6/10 | Isolated harness (`PlatformHardeningRegressionE2E.harness.py`, 10 scenario's) |
| 7/10 | pytest: `test_file_tools_fork_patch` + `test_file_tools` + sandbox + hardware + lancedb + vector_store + knowledge_repository |
| 8/10 | Footguns op gewijzigde modules |
| 9/10 | Architecture modules (`knowledge_repository`, `vector_store_*`) |
| 10/10 | ingest + MCP wired via `KnowledgeRepository` |

Optioneel: `-SkipPytest` op `RUN_PLATFORM_HARDENING_REGRESSION_E2E.ps1`.

Rapport: `PLATFORM_HARDENING_REGRESSION_E2E_REPORT_*.md`.

## Platform hardening productie-poort

```text
windows\audits\RUN_PLATFORM_HARDENING_PRODUCTION_GATE.bat
```

Gecombineerde poort (zoals `RUN_MEMORY_PRODUCTION_GATE.bat`):

1. `RUN_WINDOWS_PLATFORM_HARDENING_E2E` (10/10)
2. `RUN_PLATFORM_HARDENING_REGRESSION_E2E` (10/10)
3. pytest platform-hardening subset (`test_file_tools_fork_patch`, `test_file_tools`, `test_filesystem_sandbox`, hardware, RAG)
4. `check-windows-footguns.py --all`

Rapport: `PLATFORM_HARDENING_PRODUCTION_GATE_REPORT_*.md`. Zie `docs/WINDOWS_PLATFORM_HARDENING.md`.

## KnowledgeRepository E2E

```text
windows\audits\RUN_KNOWLEDGE_REPOSITORY_E2E.bat
```

Dedicated audit voor de RAG agent-API (`knowledge_repository.py`) en caller-migratie (ingest, MCP, maintenance).

| Stap | Controle |
| ---- | -------- |
| 1/8 | Repo-artefacten (repository, vector_store_*, callers, tests) |
| 2/8 | Edge-case API: lege search, upsert `id`-validatie, merge-fout wrap, `Callable` types |
| 3/8 | MCP shutdown via `get_vector_store_backend()` (niet `_get_repo()` bij import) |
| 4/8 | Ingest `_upsert_chunk_rows(..., repo=repo)` threading |
| 5/8 | Isolated harness (`KnowledgeRepositoryE2E.harness.py`, 8 scenario's) |
| 6/8 | pytest `test_knowledge_repository.py` (47 tests) |
| 7/8 | `lancedb_maintenance` lazy `KnowledgeRepository.session()` |
| 8/8 | Footguns op RAG callers |

Optioneel: `-SkipPytest` op `RUN_KNOWLEDGE_REPOSITORY_E2E.ps1`.

Rapport: `KNOWLEDGE_REPOSITORY_E2E_REPORT_*.md` (gitignored). Zie `docs/WINDOWS_PLATFORM_HARDENING.md` § KnowledgeRepository.

## Hermes Python institutional E2E

```text
windows\audits\RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.bat
```

Dedicated audit voor institutioneel Python-beleid: conda `hermes-env` als enige canonieke interpreter, IDE-sync, venv-quarantaine.

| Stap | Controle |
| ---- | -------- |
| 1/8 | Repo-artefacten (HermesPythonPolicy, ensure/sync scripts, REPAIR, tests) |
| 2/8 | Policy helpers + venv-quarantaine `try/catch` op `Rename-Item` |
| 3/8 | REPAIR/ensure `-SyncIde` wiring |
| 4/8 | `.vscode/settings.json` canonieke interpreter + `activateEnvironment: false` |
| 5/8 | Isolated harness (`HermesPythonInstitutionalE2E.harness.ps1`, 8 scenario's) |
| 6/8 | pytest `test_hermes_python_institutional.py` |
| 7/8 | Runtime conda hermes-env + pip |
| 8/8 | Docs (`HERMES_START.md`, `INSTITUTIONAL.md`) |

Optioneel: `-SkipPytest` op `RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.ps1`.

Rapport: `HERMES_PYTHON_INSTITUTIONAL_E2E_REPORT_*.md` (gitignored). Zie `docs/HERMES_START.md` § Python institutioneel.

## Hermes Python institutional regression E2E

```text
windows\audits\RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat
```

Validatie van code-review fixes (naast basis Python institutional E2E).

| Stap | Controle |
| ---- | -------- |
| 1/8 | Repo-artefacten (policy, bootstrap, REPAIR-check, pytest) |
| 2/8 | Policy: `HERMES_CONDA_ROOT`, `rag_extras_verified`, manifest fast-path |
| 3/8 | `launch_bootstrap.ps1`: fast-path + `Write-HermesLaunchBootstrapState` |
| 4/8 | `check_hermes_rag_after_repair.ps1`: `-NonInteractive` / `HERMES_NONINTERACTIVE` / `IsInputRedirected` |
| 5/8 | Isolated harness (`HermesPythonInstitutionalRegressionE2E.harness.ps1`, 9 scenario's) |
| 6/8 | pytest `test_hermes_python_institutional.py` (40+ tests) |
| 7/8 | Setup gebruikt canonieke bootstrap stamp (`Sync-HermesLaunchBootstrapStamp`) |
| 8/8 | `install_rag_extras.ps1`: manifest alleen na geverifieerde RAG-import |

Optioneel: `-SkipPytest` op `RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.ps1`.

Rapport: `HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E_REPORT_*.md` (gitignored). Zie `docs/INSTITUTIONAL_OPERATIONS.md`.

## Institutional production gate

```text
windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat
```

| Volgorde | Audit |
|----------|-------|
| 1 | `RUN_HERMES_PYTHON_INSTITUTIONAL_E2E` (8/8) |
| 2 | `RUN_KNOWLEDGE_REPOSITORY_E2E` (8/8) |
| 3 | `RUN_PLATFORM_HARDENING_PRODUCTION_GATE` |
| 4 | `..\audits\RUN_INSTITUTIONAL_HARDENING_E2E` (14/14 — repo-hygiene, QuickFix, legal pytest) |
| 5 | `validate_windows_python_wiring.ps1` |
| RUN_AUDITS | `-IncludeInstitutionalHardeningE2E` / `-IncludeRepoHygieneE2E` / `-IncludeUpdateHermesIntegrationE2E` (los van productie-poort) |
| Optioneel | `-IncludeMemoryGate` → memory production gate |

Pytest-equivalent (Windows): `pytest tests\windows\test_repo_hygiene_institutional_e2e.py -m e2e`

Optioneel: `-SkipPytest` op onderliggende E2E's.

Rapport: `INSTITUTIONAL_PRODUCTION_GATE_REPORT_*.md`. Zie `docs/INSTITUTIONAL_OPERATIONS.md`.

## Memory-architectuur E2E (L1–L4)

```text
windows\audits\RUN_MEMORY_ARCHITECTURE_E2E.bat
```

Optioneel: `-SkipSyncRun` (geen live `sync_hermes_api_env.ps1`).

| Stap | Controle |
| ---- | -------- |
| 1/18 | Repo: trust-sync, merge-common, consolidate-root, rebalance |
| 2–7 | Legacy/runtime vault-env, sync-script, profiel-.env, vault-structuur, geen L3 |
| 8–10 | KANBAN + core MEMORY, obsidian skill, config-limits 4000/1800 |
| 11–13 | core MEMORY-grootte, UTF-8 §-encoding |
| 14/16 | **Alle 13 profielen:** MEMORY/USER binnen limiet, geen dubbele §, geen mojibake |
| 15/16 | Repo: `deduplicate_memories.py`, `Invoke-MemoryTrustPostSync`, notice-module |
| 16–18 | TUI auto `/new`; consolidatie-layout; §-delimiter U+00A7 |

**Productie-poort:** `RUN_MEMORY_PRODUCTION_GATE.bat` = bovenstaande + trust forensic E2E + pytest (`test_deduplicate_memories`, `test_institutional_new_chat_notice`, …).

**Niet in deze E2E:** live Ink-TUI pixel-test van auto `/new` (vitest: `newChatNotice.test.ts`, `createGatewayEventHandler.newChatNotice.test.ts`).

Zie `docs/MEMORY_ARCHITECTURE.md`, `docs/TRUST_FORENSIC_PROTOCOL.md`.

## Statusbalk-kosten E2E (rich)

```text
windows\audits\RUN_STATUS_BAR_COST_E2E.bat
```

Optioneel: `-ApplyDisplayFix` (display drift), `-SkipRuntime` (geen Hermes home), `-SkipVitest`.

| Stap | Controle |
| ---- | -------- |
| 1/10 | Repo: `show_cost=true`, `cost_bar_mode=rich`, fork-owned modules |
| 2/10 | Institutional/diagnose drift + `merge_upstream_fork.ps1` keepOurs |
| 3/10 | Vitest: `statusBarCost`, `usageCostBar`, `createGatewayEventHandler` turn/tools |
| 4/10 | Pytest: snapshot, E2E module, gateway `cost` + `cost_bar_mode` config |
| 5/10 | Runtime root: `show_cost` + `cost_bar_mode: rich` |
| 6/10 | Alle profielen: idem |
| 7/10 | Gateway smoke: `cost_usd` + `cost_breakdown_pct` (som 100%) |
| 8/10 | `verify_usage_cost_bar.py --verify` |
| 9/10 | `UPSTREAM_SYNC.md` conflict-tabel |
| 10/10 | `ui-tui/README.md` documenteert `/cost`, `config.set cost_bar_mode`, live `~$turn` |

**Niet in deze E2E:** live Ink-TUI pixel-render (handmatig: statusbalk tijdens stream). Onbekende modelprijs (`cost_usd` ontbreekt) toont in de TUI `n/a`/`included` plus live `~NK tok` tijdens stream — gedekt via vitest (`liveTurnCost`, `usageCostBar`, `createGatewayEventHandler`).

## Klassieke CLI statusbalk-kosten E2E

```text
windows\audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat
```

Optioneel: `-SkipPytest` (alleen repo/smoke/verify).

| Stap | Controle |
| ---- | -------- |
| 1/12 | Repo: `status_bar_cost.py`, `usage_snapshot.py`, `usage_pricing.py`, `cli.py`, tests, smoke + live smoke scripts |
| 2/12 | `cli.py` hooks + formatter functies |
| 3/12 | `CommandDef("cost")` + `merge_upstream_fork.ps1` keepOurs |
| 4/12 | `UPSTREAM_SYNC.md` Classic CLI parity sectie |
| 5/12 | Pytest: `test_status_bar_cost.py` |
| 6/12 | Pytest: `test_cli_status_bar.py` (incl. `/cost`) |
| 7/12 | Pytest: `test_status_bar_cost_e2e.py` |
| 8/12 | Smoke: `status_bar_cost_classic_cli_smoke.py` |
| 9/12 | **Live post-turn:** `status_bar_cost_classic_cli_live_smoke.py` (snapshot + fragments, `/cost`, **gemini-3.5-flash cache ≠ n/a**, subprocess-isolatie) |
| 10/12 | `verify_usage_cost_bar.py --verify` (incl. Google cache catalog) |
| 11/12 | Docs: `cli.md`, `TERMINAL_WINDOWS.md`, `configuration.md`, `config.py` |
| 12/12 | **Gemini cache pricing:** `_GOOGLE_GEMINI_PRICING`, `_seed_agent_session_cost`, pytest `test_usage_pricing` + `test_usage_snapshot` (gemini cache) |

Optioneel: `-SkipPytest` voor alleen repo/smoke/verify/docs.

## Pareto Code router E2E

```text
windows\audits\RUN_PARETO_E2E.bat
```

Optioneel: `-SkipPytest` (alleen repo/verify/docs).

| Stap | Controle |
| ---- | -------- |
| 1/8 | Repo: openrouter plugin, transport, helpers, config, verify script |
| 2/8 | Plugin model-gate `openrouter/pareto-code` + `pareto-router` |
| 3/8 | `chat_completions.py` + `chat_completion_helpers.py` parity |
| 4/8 | `config.py` `min_coding_score` + `models.py` catalog |
| 5/8 | Pytest transport `-k openrouter_pareto` |
| 6/8 | Pytest `test_pareto_e2e.py` + provider profiles `-k pareto` |
| 7/8 | `verify_pareto_router.py --verify` |
| 8/8 | Docs: `providers.md` + `configuration.md` |

**Niet in deze E2E:** live OpenRouter API-call (router kiest daadwerkelijk model); handmatig met `model: openrouter/pareto-code` + `openrouter.min_coding_score`.

Rapport: `PARETO_E2E_REPORT_<timestamp>.md` in deze map — **gitignored** (zelfde patroon als `*_E2E_REPORT_*_*.md`).

## Codebase smoke audit

```text
windows\audits\RUN_CODEBASE_SMOKE_E2E.bat
windows\audits\RUN_CODEBASE_SMOKE_AUDIT.bat
windows\audits\RUN_CODEBASE_SMOKE_AUDIT.bat -IncludePygount
windows\audits\RUN_AUDITS.bat -IncludeCodebaseSmokeE2E
windows\audits\RUN_AUDITS.bat -IncludeCodebaseSmoke
```

| Stap (E2E) | Inhoud |
| ---------- | ------ |
| 1/5 | Repo-artefacten (`CODEBASE_AUDIT_*`, runners, tests) |
| 2/5 | Strict denylist op `docs/templates/CODEBASE_AUDIT_REPORT.md` |
| 3/5 | `pytest tests/windows/test_codebase_smoke_audit.py` |
| 4/5 | `RUN_CODEBASE_SMOKE_AUDIT` (verify-keten, SessionDB, TUI collect-only, …) |
| 5/5 | Institutioneel rapport (E-tiers, geen E3) |

Rapporten: `CODEBASE_SMOKE_E2E_REPORT_<timestamp>.md` (gitignored via `*_E2E_REPORT_*_*.md`), `CODEBASE_SMOKE_AUDIT_REPORT_*.md`, `CODEBASE_SMOKE_STEPLOG_*.json`. Zie [CODEBASE_AUDIT_EVIDENCE.md](../../docs/CODEBASE_AUDIT_EVIDENCE.md).

## IDE-onderhoud E2E (volledige landkaart)

```text
windows\audits\RUN_IDE_MAINTENANCE_E2E.bat -ApplyDisplayFix
```

**15 stappen** (landkaart categorie I-V): repo-artefacten → verify-keten → setup-wrapper pytest → IDE pytest (merge/LanceDB/display) → `LANCEDB_MAINTENANCE.bat --list` → schema `--inspect` → `audit_skill_drift.py` → merge git-diff snippet → (optioneel) `MERGE_UPSTREAM -PromptOnly` → display-fix → `diagnose_renderer --verify` → score ≥9.0 → normalizer-pariteit → institutional guard → `.vscode` + `python-conda.mdc` → LanceDB benchmark (core, 500ms).

| Vlag | Effect |
| ---- | ------ |
| `-ApplyDisplayFix` | `apply_team_display.ps1` vóór diagnose (root + profielen) |
| `-SkipMergePreview` | Geen `git fetch` / merge-tree (sneller) |
| `-Full` | `-ApplyDisplayFix` + `RUN_INSTITUTIONAL_E2E` (11/11) |
| `-IncludeInstitutional` | Alleen institutioneel E2E extra |

Rapport: `IDE_MAINTENANCE_E2E_REPORT_<timestamp>.md`. Baseline: `IDE_MAINTENANCE_BASELINE_2026-05-23.md`.

**Niet in deze E2E:** volledige `RUN_AUDITS` (ruff/footguns), legal/toolset E2E, LanceDB `--compact` (destructief; handmatig).

## Domein-toolsets E2E

```text
windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat
```

Of via gecombineerde poort:

```text
windows\audits\RUN_AUDITS.bat -IncludeToolsetDomainE2E
```

| Stap | Controle |
| ---- | -------- |
| 1/6 | `verify_hermes_home` (+ auth.json repair indien corrupt) |
| 2/6 | Repo: `domain_toolsets.yaml`, audit-doc, sync-scripts |
| 3/6 | pytest: manifest + lege `cli: []` (geen hermes-cli/MCP/kanban-lek) |
| 4/6 | Runtime drift: `sync_profile_toolsets_from_manifest.py --check` |
| 5/6 | Per profiel: `platform_toolsets.cli`, tool-count ≤ `max_tools`, root = **0 tools** |
| 6/6 | SOUL: Tool governance in `core` + `legal` |

**Vóór audit (bij drift):** `windows\SYNC_DOMAIN_TOOLSETS.bat`

**Schone machine / ontbrekend profiel in manifest:** eerst `windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing` (zet `HERMES_HOME` op root, niet `profiles\legal`). Smoke: `RUN_PROVISION_DOMAIN_E2E.bat`.

**Rapport:** `TOOLSET_DOMAIN_E2E_LAST_RUN.log` (gitignored)

**Handmatig na PASS:** nieuwe chat met `hermes -p <domein>` — root zonder `-p` heeft bewust geen tools.

Zie `docs/DOMAIN_TOOLSET_AUDIT.md`.

## Hermes split-home E2E

```text
windows\audits\RUN_HERMES_HOME_E2E.bat
windows\APPLY_HERMES_HOME_MIGRATION.bat
```

Optioneel: `-SkipPytest` op `RUN_HERMES_HOME_E2E.ps1`.

| Stap | Controle |
| ---- | -------- |
| 1/14 | Repo-artefacten (HermesHomeCommon, migration, merge Venice, presets, docs) |
| 2/14 | pytest: doctor split-home, inheritance, merge, constants, config |
| 3/14 | `Get-HermesRuntimeRoot` consistent across modules |
| 4/14 | Geen actieve `~/.hermes/config.yaml` |
| 5/14 | Legacy hub: `CONFIG_README.txt` of `config.yaml.deprecated-*` |
| 6/14 | `inventory_hermes_home.ps1 -Quiet` |
| 7–8/14 | `verify_hermes_home` + `verify_hermes_config_drift` |
| 9/14 | `Ensure-UserHermesHomeRoot` proces-env |
| 10/14 | User `HERMES_HOME` = runtime root (geen `profiles\*`) |
| 11/14 | Gateway HERMES_HOME aligned |
| 12/14 | Geen `model`/`auxiliary`/`providers` in profiel-yaml |
| 13/14 | Venice provider in root config |
| 14/14 | `VENICE_API_KEY` gesynced naar runtime `.env` |
| + | `auxiliary.vision.provider=gemini`; core erft `auxiliary.compression.provider=custom` |

**Productie-poort:** `APPLY_HERMES_HOME_MIGRATION.bat` = backup → deprecate → preset → Venice merge → strip → env sync → deze E2E.

Rapport: `HERMES_HOME_E2E_REPORT_<timestamp>.md` (gitignored via `*_E2E_REPORT_*_*.md`).

Zie `docs/HERMES_HOME_WINDOWS.md`.

## Model/provider coherence E2E

```text
audits\RUN_MODEL_PROVIDER_COHERENCE_E2E.bat
```

Of via `windows\audits\RUN_MODEL_PROVIDER_COHERENCE_E2E.bat` (delegate). Optioneel in `RUN_AUDITS.bat`: `-IncludeModelProviderCoherenceE2E`.

| Stap | Controle |
| ---- | -------- |
| E1–E10 | Harness `audits/ModelProviderCoherenceE2E.harness.py`: root persist vanuit profiel, detect (split-brain, vendor-slug, base_url), repair, auth-sync, custom `api_key`, minimale auth.json |

Geen live API. Zie `audits/README.md` en `docs/HERMES_HOME_WINDOWS.md` § split-brain.

## Model/provider hardening E2E

```text
audits\RUN_MODEL_PROVIDER_HARDENING_E2E.bat
```

Of `windows\audits\RUN_MODEL_PROVIDER_HARDENING_E2E.bat`. Optioneel: `RUN_AUDITS.bat -IncludeModelProviderHardeningE2E` of `-IncludeAllE2E`.

| ID | Scenario |
|----|----------|
| E1 | YAML global blocks — geen false positive op comments |
| E2 | `strip_all_profile_global_blocks` verwijdert echte keys |
| E3 | Drift-gate: alleen error-severity blokkeert |
| E4–E5 | `read_auth_json` leeg + BOM |
| E6 | Corrupt auth + repair guard |
| E7 | Nous shared store BOM |
| E8 | Azure Foundry persist + auth sync |

Harness: `audits/ModelProviderHardeningE2E.harness.py`. Unit tests: `tests/overlay/test_auth_json_store.py`, `test_profile_model_inheritance.py`. Zie `audits/README.md`.

## Root config inheritance E2E

```text
windows\audits\RUN_ROOT_CONFIG_INHERITANCE_E2E.bat
```

Optioneel: `-SkipPytest`, `-SkipLive` op `RUN_ROOT_CONFIG_INHERITANCE_E2E.ps1`.

| Stap | Controle |
| ---- | -------- |
| 1/10 | Repo-artefacten (inheritance module, merge/collect scripts, E2E harness) |
| 2/10 | pytest: `test_profile_model_inheritance.py`, `test_merge_legacy_providers_config.py` |
| 3/10 | Isolated harness: pad, env-sync, merge→root, cache-bust, save-guard, corrupt YAML, 1× root read |
| 4/10 | Code wiring + `py_compile` op `collect_env_sync_keys.py` (save guard, cache bust) |
| 5/10 | Runtime: geen profiel global blocks |
| 6/10 | Runtime: Venice in root config |
| 7/10 | `merge_legacy_providers_config.py` gebruikt `root_config_path()` |
| 8/10 | Live: `profiles/core` erft `auxiliary.compression.provider=custom` |
| 9/10 | Live: `collect_env_sync_keys.py` op runtime root |
| 10/10 | `sync_hermes_api_env.ps1` Venice + dynamic keys |

Rapport: `ROOT_CONFIG_INHERITANCE_E2E_REPORT_<timestamp>.md` (gitignored).

Zie `docs/PROFILE_MODEL_INHERITANCE.md`.

## SOUL deploy bij start E2E

```text
windows\audits\RUN_SOUL_DEPLOY_START_E2E.bat
```

| Stap | Controle |
| ---- | -------- |
| 1/8 | Repo-keten: `launch_soul_anatomy_deploy`, `launch_hermes` volgorde, `POST_GIT_PULL -Force`, geen `SOUL_ANALYST_DOMAIN` |
| 2/8 | `Get-SoulAnatomyWatchPaths`, 13 profielen |
| 3/8 | Stamp-logica (isolated temp; geen repo-touch) |
| 4/8 | `HERMES_SKIP_SOUL_DEPLOY_ON_START=1` |
| 5/8 | Productie-stamp → `up-to-date` (skip indien geen stamp) |
| 6/8 | `launch_institutional_runtime` zonder SOUL-watch, met `SkipSoul` na deploy |
| 7/8 | `sync_all` exit-codes + `-UpdateDeployStamp` |
| 8/8 | `RUN_SOUL_ANATOMY_E2E` (runtime anatomy) |

**Rapport:** `SOUL_DEPLOY_START_E2E_LAST_RUN.log` (gitignored indien in .gitignore)

**Handmatig na FAIL stap 5:** `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat`

## Profielwissel E2E

```text
Dubbelklik of: windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Stappen: HERMES_HOME-root check → unit tests → `SWITCH_PROFILE.bat legal` → smoke `HERMES_HOME=profiles\core` + `-p legal` → sticky terug naar `core`.

Sync naar `%USERPROFILE%\.hermes\_local_assets\` kopieert dit README + audit-runners mee waar geconfigureerd.

## Landkaart-skill

Na `git pull` of `UPDATE_HERMES.bat`: nieuwe sessie of `hermes update` zodat skill `landkaart` en slash `/landkaart` geladen zijn. Script: `skills/productivity/landkaart/scripts/inventory_landkaart.py` (unit tests in `tests/`).
