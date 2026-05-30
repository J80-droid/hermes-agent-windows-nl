# Launch UI Sink E2E

Geïsoleerde E2E voor console-overlap-fix, capture-contract en startketen `launch_hermes.bat` → `launch_hermes.ps1` → orchestrator. Geen live WT, geen chat.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| L1–L8 | Zie `audits/LAUNCH_UI_SINK_E2E_README.md` | Wiring, EL `[2K`, quiet log, allowlist, unit gate |

```bat
audits\RUN_LAUNCH_UI_SINK_E2E.bat
```

---

# Sessie-onderhoud (stamps) E2E

Geïsoleerde E2E voor stamp-helpers, `HermesSessionMaintenance.ps1` (start + post-pull tail), orchestrator-wiring en POST_GIT_PULL-integratie. Geen live git pull / WT-relaunch / volledige RAG.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| S1–S14 | Zie `audits/SESSION_MAINTENANCE_E2E_README.md` | Artefacten, wiring, isolated stamps, PostPullTail skips, pytest + Pester |

```bat
audits\RUN_SESSION_MAINTENANCE_E2E.bat
```

---

# Post-git-pull automatisering E2E

Geïsoleerde E2E voor `start_hermes.bat` / pull-keten → `POST_GIT_PULL.bat`, relaunch (`Invoke-HermesPostPullRelaunch.ps1`), trust-outcome, stop-script en CLI `/new`-pariteit. Dagelijks: `start_hermes.bat` (auto-pull via `Test-HermesGitPullNeeded.ps1`). Geen live WT in E2E (`HERMES_SKIP_RELAUNCH_AFTER_PULL=1`).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| P1–P14 | Zie `audits/POST_GIT_PULL_AUTOMATION_E2E_README.md` | Wiring, mocks, trust pending, RAG exit 2, pytest-subset |

```bat
audits\RUN_POST_GIT_PULL_AUTOMATION_E2E.bat
```

Unit tests (gemockt, geen live PowerShell): `pytest tests/audits/test_post_git_pull_automation_e2e_harness.py -q -m "not e2e"`. Volledige harness: `-m e2e`.

---

# Institutional pipeline E2E

Geïsoleerde E2E voor normalize → render → score hardening (single-normalize contract, `compact_institutional_check`, finalize-only streaming). Geen live API.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Repo-artefacten | Pipeline-modules, score/bench, contract tests, audit runners |
| E2 | `compact_institutional_check` | XML → `Controle  · item` |
| E3–E5 | Normalize contract | 1× normalize, `render_institutional_from_prepared`, `HERMES_STRICT_RENDER` |
| E6–E7 | Render | Geen XML in ANSI; geen valse checklist op prose |
| E8 | Streaming | Geen ANSI per chunk |
| E9–E10 | Gates | `score --verify` ≥ 9.0; pytest contract |
| E11 | TS parity | Python = Web op checklist-fixture (SKIP zonder npx) |

```bat
audits\RUN_INSTITUTIONAL_PIPELINE_E2E.bat
```

Zie `audits/INSTITUTIONAL_PIPELINE_E2E_README.md`.

---

# Dashboard on start E2E

`launch_hermes.bat` start `hermes dashboard --no-open` op poort 9119 (geen browser-tab).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| D1-D7 | Script, wiring, docs, skip env, pytest | Zie `audits/DASHBOARD_ON_START_E2E_README.md` |

```bat
audits\RUN_DASHBOARD_ON_START_E2E.bat
```

---

# Web UI clean codebase E2E

Geïsoleerde poort voor `web/`: `npm run lint` + `npm run build`, PTY-channel-contract (`resume-{id}`), hooks/context-splits, OAuth lifecycle, `apply_team_display_profiles` utils-import. Geen live browser op 9119.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| W1–W11 | Zie `audits/WEB_UI_CLEAN_E2E_README.md` | Artefacten, lint, build, web_dist, pytest |

```bat
audits\RUN_WEB_UI_CLEAN_E2E.bat
```

---

# Creative domain E2E

Geïsoleerde E2E voor profiel `creative` (14e domein): manifest, `13_Creative/`, SOUL, fork-skills, provision, pytest-subset. Geen live API.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| C1 | Repo-artefacten | Manifest, SOUL, docs, sync-scripts, tests |
| C2 | Manifest-contract | Lenzen, `terminal`, fork_skills, ask_triggers, max_tools |
| C3 | Fork-skills op schijf | `skills/` + `optional-skills/creative/hyperframes` |
| C4 | `domains.yaml.example` | `13_Creative`, `lancedb-creative` |
| C5 | Orchestrator-routing | `ORCHESTRATOR_ROUTING`, blueprint |
| C6 | `SyncSoulSnippet` | 14 profielen incl. `creative` |
| C7 | Backup | `CREATIVE_ACTIVE_MATTERS.md` in `HermesBackupCommon.ps1` |
| C8 | SOUL-template | Lenzen, trust, hyperframes/manim |
| C9 | pytest subset | creative manifest/docs/provision tests |
| C10 | Temp provision | Geïsoleerde `HERMES_HOME`, geen trust-memory side-effect |
| C11 | Runtime drift | Optioneel: `--profile creative --check` |

```bat
audits\RUN_CREATIVE_DOMAIN_E2E.bat
```

Unit tests: `pytest tests/audits/test_creative_domain_e2e_harness.py -q` (mocks; `-m e2e` = volledige harness). Zie `audits/CREATIVE_DOMAIN_E2E_README.md`.

---

# Codebase Viz dashboard E2E

Geïsoleerde E2E voor bundled plugin `codebase-viz` (structuur, metrics, doctor, parsers). Geen browser; wel TestClient + tiny repo.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| V1 | Repo-artefacten | manifest, `plugin_api.py`, `dist/*`, unit tests |
| V2 | Manifest | id `codebase-viz`, versie 2.5.0 |
| V3–V5 | Parsers/paden | Pygount 3.x, invalid JSON, `_path_under_root` |
| V6 | Env | Ongeldige `CODEBASE_VIZ_REPO` → None |
| V7–V9 | API | health, structure, summary, force-scan |
| V10 | WebSocket | Ongeldig token geweigerd |
| V12–V15 | Sprint 2 | bron + dist markers + `/dependencies` + `wsAuth` |
| V16–V18 | Hardening | `no_repo` deps, JSON type-guard, pygount timeout |

### Codebase Viz Sprint 3 E2E (geïsoleerd)

```bat
audits\RUN_CODEBASE_VIZ_SPRINT3_E2E.bat
```

Zie `audits/CODEBASE_VIZ_SPRINT3_E2E_README.md` (S1–S9: todos, search, history parser, cycles, API mocks).
| V11 | pytest gate | `tests/plugins/test_codebase_viz_plugin.py` |

```bat
audits\RUN_CODEBASE_VIZ_E2E.bat
```

Zie `audits/CODEBASE_VIZ_E2E_README.md` en `plugins/codebase-viz/dashboard/README.md`.

### Codebase Viz pygount disk-cache E2E

| Script | Doel |
|--------|------|
| `RUN_CODEBASE_VIZ_PYGOUNT_CACHE_E2E.bat` | Pre-warm script, skip `backups/`, disk-cache, launch wiring, tiny-repo roundtrip (8/8) |

Zie `audits/CODEBASE_VIZ_PYGOUNT_CACHE_E2E_README.md`.

### Codebase Viz productie E2E

| Script | Doel |
|--------|------|
| `RUN_CODEBASE_VIZ_PRODUCTION_E2E.bat` | Timeout/scan-status telemetry, launch/RESTART wiring, dist UI (structureel) |
| `RUN_CODEBASE_VIZ_INCREMENTAL_SWR_E2E.bat` | SWR/incremental mode, snapshot data hashes, signature-delta fallback |
| `RUN_CODEBASE_VIZ_LAUNCH_E2E.bat` | Dashboard launch integratie (7 checks) |

```bat
audits\RUN_CODEBASE_VIZ_SPRINT4_E2E.bat
```

Zie `audits/CODEBASE_VIZ_SPRINT4_E2E_README.md` (H1–H9: memory guard, thundering herd, dist markers, example dist).

### Codebase Viz live dashboard E2E (9119)

Loopback audit voor `http://127.0.0.1:9119/codebase-viz`: bronscripts, dist CSS-contract (dropdown), launch wiring, live API smoke (als dashboard draait).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| L1–L5 | Artefacten, routes, frontend, CSS, launch | Zie `audits/CODEBASE_VIZ_LIVE_E2E_README.md` |
| L7–L14 | Live HTTP | `/codebase-viz`, assets, health, API smoke, 401 zonder token |
| L15 | pytest gate | `test_codebase_viz_plugin.py` |

```bat
audits\RUN_CODEBASE_VIZ_LIVE_E2E.bat
```

Rapport: `audits/CODEBASE_VIZ_LIVE_AUDIT_REPORT_2026-05-29.md`

---

# Prompt timer display (geen emoji) E2E

Geïsoleerde E2E voor `display.show_prompt_timer_emoji` (default **uit**), fork-module `status_bar_prompt_elapsed.py`, cli-delegatie en upstream-verify. Geen live API.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Repo-artefacten | module, verify-script, tests, audit runners, merge keepOurs |
| E2 | Module | `26s` zonder emoji; NaN/future → `0s`; emoji aan = U+23F2 prefix |
| E3 | Config + team defaults | `show_prompt_timer_emoji: false` overal |
| E4 | cli.py | delegatie + `is_truthy_value` + `/timer-emoji` |
| E5 | Verify-script | `verify_fork_status_bar_display.py` PASS |
| E6 | Classic CLI | snapshot + `_build_status_bar_text` zonder ⏱/⏲ |
| E7 | Slash + persist | `timer-emoji` in commands + `save_config_value` |
| E8 | Upstream merge | `merge_upstream_fork.ps1` keepOurs |
| E9–E10 | Unit gates | 72× module tests + 2× cli `prompt_elapsed` (pytest of inline fallback) |

```bat
audits\RUN_PROMPT_TIMER_DISPLAY_E2E.bat
```

Na upstream-merge: `python scripts/verify_fork_status_bar_display.py`.

---

# Status bar throughput (tok/s) E2E

E2E voor `display.show_status_bar_tps`, classic CLI statusbalk en ui-tui parity. Geen live API.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Repo-artefacten | `status_bar_throughput.py`, cli/tui hooks, tests, audit runners |
| E2 | cli.py plaatsing | Throughput-segment **na** cost (`_append_status_bar_throughput_*`) |
| E3 | `/tps` + config default | `commands.py`, `show_status_bar_tps: true` |
| E4 | Gateway RPC | `config.get/set` key `status_bar_tps` / `tps` |
| E5 | Agent tracking | `record_agent_stream_delta` + `finalize_agent_call_tps` |
| E6 | Freeze guard | CLI `_freeze_stream_tps_segment` overschrijft agent-TPS niet |
| E7 | Formatter edges | NaN, min elapsed 0.5s, breedte ≥76, agent > CLI snapshot |
| E8–E9 | Pytest gates | `test_status_bar_throughput.py`, cli status bar `-k throughput` |
| E10 | Classic smoke | `scripts/status_bar_throughput_classic_cli_smoke.py` |
| E11 | ui-tui npm | `statusBarThroughput.test.ts` + layout reserve |

```bat
audits\RUN_STATUS_BAR_THROUGHPUT_E2E.bat
```

Unit tests: `pytest tests/hermes_cli/test_status_bar_throughput.py tests/cli/test_cli_status_bar.py -k "throughput or tok"`; classic smoke: `python scripts/status_bar_throughput_classic_cli_smoke.py`.

| E12–E14 | Prompt-timer zonder emoji | `status_bar_prompt_elapsed.py`, config default, `verify_fork_status_bar_display.py`, pytest |

Na upstream-merge: `python scripts/verify_fork_status_bar_display.py`.

---

# Model/Provider Coherence E2E

Geïsoleerde E2E voor `persist_model_runtime`, coherence-detectie en repair. Geen live API-calls.

## Scenario's

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | `HERMES_HOME=profiles/core`, persist nous | Root `model.provider=nous`, profiel zonder `model:` |
| E2 | auth=nous, config=gemini | `auth_config_provider_mismatch` |
| E3 | nous + Gemini `base_url` | `base_url_provider_mismatch` |
| E4 | gemini + vendor-slug default | `vendor_slug_wrong_provider` |
| E5 | split-brain + repair | provider=nous, geen Gemini-host, coherent |
| E6 | persist openrouter | `auth.active_provider=openrouter` (niet gewist) |
| E7 | één persist-call | provider + default samen in root yaml |
| E8 | custom + `extra_model_fields` | `api_key` en `api_mode` behouden |
| E9 | minimale auth.json | mismatch nog steeds gedetecteerd |
| E10 | aligned nous config | geen issues |

## Uitvoeren

```bat
audits\RUN_MODEL_PROVIDER_COHERENCE_E2E.bat
```

Of via `RUN_AUDITS.bat -IncludeModelProviderCoherenceE2E` (windows/audits delegateert naar deze harness).

---

# Model/Provider Hardening E2E

Aanvullende E2E voor code-review hardening (geen live API).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Profiel-yaml met comment `# providers:` | Geen false-positive global blocks |
| E2 | Echte `auxiliary`/`providers` keys | Gedetecteerd + gestript |
| E3 | vendor_slug warn op gemini | Geen blocking errors (drift-gate) |
| E4 | Lege auth.json | `read_auth_json` → `{}` |
| E5 | auth.json met UTF-8 BOM | Parse OK |
| E6 | Corrupt auth.json | Lege store + guard reset |
| E7 | Nous shared store BOM | `_read_shared_nous_state` OK |
| E8 | `persist_model_runtime(azure-foundry)` | Coherent + auth sync |

```bat
audits\RUN_MODEL_PROVIDER_HARDENING_E2E.bat
```

Windows delegate: `windows\audits\RUN_MODEL_PROVIDER_HARDENING_E2E.bat`

`RUN_AUDITS.bat -IncludeModelProviderHardeningE2E` (of `-IncludeAllE2E`).

---

# Collapsed record pseudo-table E2E

Dedicated audit voor ingeklapte `Component`/`Keuze`/`Status`-regels met em-dash of multi-line (review hardening + eligibility guard).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Em-dash op één regel | `\| Component \| Keuze \| Status \|` + geen em-dash restant |
| E2 | Multi-line zonder em-dash | Anchor-key split → ≥2 datarijen |
| E3 | Kop Architectuursamenvatting | intent `overview` + `_parse_section_to_table` |
| E4 | **Groep** + Provider/Model | Geen record-parser; 4-koloms auxiliary-tabel |
| E5 | Pipe in celwaarde | `\|` → ` / ` in tabel |
| E6 | Bestaande markdown-tabel | Idempotent (1 divider) |
| E7 | `verify_pseudo_table_normalizer.py` | Architectuur-probe PASS |
| E8 | discover + dedupe helpers | Keys + unieke rijen |
| E9 | `normalize_assistant_markdown` | Volledige pipeline |
| E10 | TS parity (Web runner) | Zelfde output als Python |

```bat
audits\RUN_COLLAPSED_RECORD_PSEUDO_TABLE_E2E.bat
```

Unit tests (geen live API): `pytest tests/hermes_cli/test_collapsed_record_pseudo_table.py` — happy path, edge cases (pipe in cel, dedupe, eligibility), negatieve input; mocks op interne helpers waar nodig.

Uitvoeren vanuit repo-root `hermes-agent\` (zelfde patroon als andere `audits\RUN_*` runners).

---

# Classic CLI pending queue E2E

Geïsoleerde E2E voor `_pending_input` wachtrij: `/queue` list/pop/clear, compact hint-paneel, statusbalk `queue:N`. Geen live API, geen volledige TUI.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | FIFO snapshot (3 items) | Volgorde first → third |
| E2 | `render_queue_lines` list_mode | Max 8 regels + `…and N more` |
| E3 | `pop_pending_head` | Head weg, rest behouden |
| E4 | `clear_pending_queue` | Depth 0, count=2 |
| E5 | Pop lege queue | `None`, geen crash |
| E6 | Slash in queue | `[cmd]` prefix |
| E7 | Tuple + images | `[N images]` suffix |
| E8 | `enqueue_ack_message` | `next turn` vs `when idle` |
| E9 | `queue_status_fragment` | Alleen bij depth > 0 |
| E10 | Smalle terminal hint | `/queue list` + `hint_panel_height=2` |
| E11 | `format_removed_preview` | ANSI-strip + ellipsis |
| E12 | HermesCLI 3× enqueue | Snapshot FIFO |
| E13 | HermesCLI pop + clear | FIFO + leeg |
| E14 | HermesCLI `/q` alias | Queue, niet quit |
| E15 | `_command_running` | `_queue_hint_blocked` |
| E16 | Statusbalk helper | `queue:1` fragment |
| E17 | pytest gate | `test_cli_pending_queue` + queue-filter `test_cli_init` |

```bat
audits\RUN_CLI_PENDING_QUEUE_E2E.bat
```

Unit tests: `pytest tests/hermes_cli/test_cli_pending_queue.py tests/cli/test_cli_init.py -k "queue or pending"`.

---

# Legal production E2E

Geïsoleerde E2E voor legal P0–P3 (slash, SOUL-meta, parity, pytest-contract, runtime verify). Geen live LLM.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| S1–S17 | Zie `audits/LEGAL_PRODUCTION_E2E_README.md` | Artefacten, brief, parity, lens smoke, pytest bundle, SOUL sync, strict verify |

```bat
audits\RUN_LEGAL_PRODUCTION_E2E.bat
```

Unit tests (gemockt): `pytest tests/audits/test_legal_production_e2e_harness.py tests/scripts/test_verify_legal_lens_parity.py tests/hermes_cli/test_legal_architecture_brief.py tests/scripts/test_legal_lens_from_path.py -q`.

Zwaardere runtime-poort: `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat`.

---

# Legal memory language layers E2E

Geïsoleerde E2E voor **taal per laag** (EN trust + 3× NL legal USER, SOUL precedence, geen i18n). Geen SOUL repair/Pester.

```bat
audits\RUN_LEGAL_MEMORY_LANGUAGE_LAYERS_E2E.bat
```

Zie `audits/LEGAL_MEMORY_LANGUAGE_LAYERS_E2E_README.md`. Unit (gemockt): `pytest tests/audits/test_legal_memory_language_layers_e2e_harness.py -q`.

# Legal proactive sparring E2E

Geïsoleerde E2E voor **parallelle invalshoeken**, **Config governance duplicate-repair**, **legal USER.md seed** en **LEGAL_ACTIVE_MATTERS Adjacent checks**. Geen live LLM.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| S1–S14 | Zie `audits/LEGAL_PROACTIVE_SPARRING_E2E_README.md` | Templates, script-contract, pytest meta-contract, Pester repair, `LegalProactiveSparringE2E.core.ps1`, runtime SOUL/USER/MATTERS |

```bat
audits\RUN_LEGAL_PROACTIVE_SPARRING_E2E.bat
```

Auto: `APPLY_SOUL_ANATOMY_RUNTIME.bat`, `launch_soul_anatomy_deploy.ps1` (bij deploy), `SYNC_TRUST_RUNTIME.bat`, `RUN_AUDITS -IncludeLegalDomainE2E`. Skip: `HERMES_SKIP_LEGAL_PROACTIVE_E2E=1`; trust alleen: `HERMES_LEGAL_PROACTIVE_E2E_ON_TRUST=0`.

Unit tests (gemockt): `pytest tests/audits/test_legal_proactive_sparring_e2e_harness.py -q`. Pester: `windows\tests\SoulSnippetRepair.Unit.Tests.ps1`.
