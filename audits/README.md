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
