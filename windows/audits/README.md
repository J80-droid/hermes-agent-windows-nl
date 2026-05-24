# Windows audits (optioneel)

Deze map bevat de **fork** kwaliteitspoorten (geen 1:1 upstream-kloon).

**IDE-markeringen op audit-`.ps1`?** Rode strepen kunnen verouderde PowerShell-extensie-cache zijn. Verifieer met:

```bat
windows\audits\VALIDATE_AUDIT_PS1_SYNTAX.bat
```

Daarna in Cursor: Command Palette → `PowerShell: Restart Session` en `Developer: Reload Window`.

**PSES-valkuil:** in single-quoted strings faalt de IDE-parser soms op paden met extensie (bijv. `'README.md'` → `.md` buiten de string). Gebruik dubbele quotes (`"README.md"`) of concatenatie (`'README' + '.md'`). Runtime/AST is dan wél correct — vertrouw op `VALIDATE_AUDIT_PS1_SYNTAX.bat`.

**Trust E2E:** `RUN_TRUST_FORENSIC_E2E.ps1` is alleen een launcher; logica staat in `TrustForensicE2E.core.ps1` (dot-source naar `HermesTrustForensicPatterns.ps1`, `HermesTrustForensicProfileChecks.ps1`, `MemoryAuditCommon.ps1`). BAT en `RUN_AUDITS` blijven de launcher aanroepen.

**Classic CLI statusbalk E2E:** `RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1` is alleen een launcher; logica staat in `ClassicCliStatusBarCostE2E.core.ps1` (geen dot-source — stabiel in IDE/PSES).

**Memory E2E:** `RUN_MEMORY_ARCHITECTURE_E2E.ps1` is alleen een launcher; logica staat in `MemoryArchitectureE2E.core.ps1` (dot-source naar `MemoryAuditCommon.ps1`). Geen dot-source in de launcher — stabiel in Cursor/PSES.

| Runner | Doel |
| ------ | ---- |
| **`RUN_CODEBASE_SMOKE_AUDIT.bat`** | Snelle smoke (E1/E2): pytest/verify-subset; rapport `CODEBASE_SMOKE_AUDIT_REPORT_*.md`. **Geen E3.** |
| **`RUN_CODEBASE_SMOKE_E2E.bat`** | E2E-poort (5 stappen): repo files + strict template + pytest wiring + smoke audit + rapport-check; `CODEBASE_SMOKE_E2E_REPORT_*.md` (gitignored) |
| **`RUN_AUDITS.bat -IncludeCodebaseSmoke`** | Alleen smoke-runner (sneller) |
| **`RUN_AUDITS.bat -IncludeCodebaseSmokeE2E`** | Volledige codebase-smoke E2E |
| **`RUN_AUDITS.bat -IncludeAllE2E`** | Inclusief codebase-smoke E2E (~30s extra) |
| **`RUN_AUDITS.bat`** | Gecombineerd: `verify_hermes_home`, PSScriptAnalyzer (SKIP indien ontbreekt), `check-windows-footguns.py`, ruff (SKIP), pytest profiel-subset |
| **`RUN_AUDITS.bat -IncludeProfileE2E`** | Bovenstaande + profielwissel E2E |
| **`RUN_AUDITS.bat -IncludeInstitutionalE2E`** | Bovenstaande + landkaart/SOUL-backup/templates E2E |
| **`RUN_AUDITS.bat -IncludeAllE2E`** | Institutioneel + legal + profielwissel + toolset + SOUL deploy-start + memory-architectuur + statusbalk-kosten E2E |
| **`RUN_SOUL_DEPLOY_START_E2E.bat`** | Stamp/startketen: launch_hermes, POST_GIT_PULL, upstream SkipSoul, anatomy subset |
| **`RUN_AUDITS.bat -IncludeSoulDeployStartE2E`** | Alleen SOUL deploy-start E2E |
| **`RUN_AUDITS.bat -IncludeToolsetDomainE2E`** | `platform_toolsets.cli` per profiel vs manifest |
| **`RUN_AUDITS.bat -IncludeLegalDomainE2E`** | Legal taxonomie, SOUL, submappen, rooktest |
| **`APPLY_INSTITUTIONAL_RUNTIME.bat`** | Handmatig: display + SOUL + E2E; **automatisch** na `UPDATE_HERMES.bat` (post-merge, `-SkipE2E`) |
| **`RUN_IDE_MAINTENANCE_E2E.bat`** | Volledige IDE-landkaart E2E (16 stappen, rapport `IDE_MAINTENANCE_E2E_REPORT_*.md`); `-Full` = display-fix + `RUN_INSTITUTIONAL_E2E`; `-SkipMergePreview` = zonder git fetch |
| **`RUN_AUDITS.bat -IncludeIdeMaintenanceE2E`** | Bovenstaande IDE-onderhoud E2E in gecombineerde poort |
| **`RUN_INSTITUTIONAL_E2E.bat`** | Audit (11 stappen incl. profiel-chat-UX); `-ApplyRuntime` = eerst runtime |
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
| **`RUN_STATUS_BAR_COST_E2E.bat`** | TUI statusbalk (rich): `show_cost`, `cost_bar_mode`, breakdown, turn-delta, live `~$turn`, gateway smoke |
| **`RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat`** | Klassieke CLI (`hermes chat`): `status_bar_cost.py`, `cli.py` hooks, `/cost`, smoke + pytest |
| **`RUN_PARETO_E2E.bat`** | OpenRouter Pareto Code router: model-gate, transport/summary parity, pytest, verify script |
| **`RUN_AUDITS.bat -IncludeMemoryArchitectureE2E`** | Bovenstaande memory E2E in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeStatusBarCostE2E`** | Bovenstaande statusbalk-kosten E2E in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E`** | Klassieke CLI statusbalk-kosten E2E in gecombineerde poort |
| **`RUN_AUDITS.bat -IncludeParetoE2E`** | Bovenstaande Pareto router E2E in gecombineerde poort |
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

Stappen: repo → pytest (landkaart, presentatie, **2d profiel-chat-UX**, **2e Rich renderer**) → landkaart smoke → backup → SOUL Interaction/Outputformaat/**5c profielwissel-regel** → display alle profielen (incl. `assistant_render_style`, `assistant_palette`, `assistant_label_columns`) → rich_output → restore/update → **pytest profielwissel** → **SWITCH legal→core** → intent-smoke.

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

Laatste rapport: `INSTITUTIONAL_E2E_REPORT_2026-05-22.md` (log `INSTITUTIONAL_E2E_LAST_RUN.log` is gitignored).  
Upstream + UPDATE audit: `UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md`.  
Memory L1–L4 audit: `MEMORY_ARCHITECTURE_E2E_REPORT_2026-05-23.md` (**16 stappen** sinds 2026-05-24; tijdelijke logs `MEMORY_ARCHITECTURE_E2E_REPORT_*_*.md` gitignored).  
Statusbalk-kosten audit: `STATUS_BAR_COST_E2E_REPORT_*.md` (10 stappen; `RUN_STATUS_BAR_COST_E2E.bat`).  
Klassieke CLI statusbalk-kosten: `CLASSIC_CLI_STATUS_BAR_COST_E2E_REPORT_*.md` (12 stappen incl. Gemini cache pricing; `RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat`).

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
windows\audits\RUN_CODEBASE_SMOKE_AUDIT.bat
windows\audits\RUN_CODEBASE_SMOKE_AUDIT.bat -IncludePygount
windows\audits\RUN_AUDITS.bat -IncludeCodebaseSmoke
```

Rapport: `CODEBASE_SMOKE_AUDIT_REPORT_<timestamp>.md` + staplog `CODEBASE_SMOKE_STEPLOG_<timestamp>.json` — **gitignored**. Zie [CODEBASE_AUDIT_EVIDENCE.md](../../docs/CODEBASE_AUDIT_EVIDENCE.md).

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
