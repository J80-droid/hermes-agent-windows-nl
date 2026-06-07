# Nous overlay-architectuur (100% intact Tier A)

## Regels

1. **Tier A (Nous)** — Bestanden die in `upstream/main` bestaan onder `agent/`, `cli.py`, `hermes_cli/`, `web/`, `ui-tui/`, enz. blijven **identiek** aan upstream na `SYNC_NOUS` (strict drift-gate).
2. **Tier B (overlay)** — `overlay/`, `windows/`, `scripts/`, tests, runtime `%LOCALAPPDATA%\hermes\`.

Fork-specifiek gedrag (statusbalk-kosten, `/cost`, Gemini-pricing, model-catalog guard) leeft in **Tier B** en wordt via bootstrap op Tier A geplakt — niet door `cli.py` of `hermes_cli/*.py` in Tier A te wijzigen.

## Sync-keten

```cmd
windows\SYNC_NOUS.bat
windows\SYNC_NOUS_DRIFT_CATCHUP.bat
```

Fasen: preflight → merge (`upstream_sync.ps1`) → `Invoke-ApplyHermesOverlay` → post-merge → drift gate + **auto catch-up** (`Invoke-HermesNousDriftGateWithCatchUp.ps1`). Geen `SYNC_NOUS -Yes` voor routine drift.

| Entry | Rol |
|-------|-----|
| `windows\UPDATE_HERMES.bat` | Dagelijkse update + drift-check na merge |
| `windows\SYNC_NOUS.bat` | Expliciete Nous-sync + overlay + drift-gate |
| `windows\scripts\Invoke-RestoreNousTierA.ps1` | Tier A terugzetten vanuit `upstream/main` vóór drift-test |

E2E sync: `windows\audits\RUN_SYNC_NOUS_E2E.bat` of `RUN_AUDITS -IncludeSyncNousE2E`.

## Bootstrap (runtime)

[`overlay/bootstrap.py`](../overlay/bootstrap.py) is de enige plek die fork-`hermes_cli.*` en `agent.*` shims registreert en runtime-patches toepast:

| Fase | Wat |
|------|-----|
| `_load_overlay_modules()` | Laadt modules uit `overlay/hermes_cli/*.py` en `overlay/agent/*.py` in `sys.modules` |
| `_apply_runtime_patches()` | Patches op `HermesCLI`, `usage_pricing`, `hermes_cli.models` |

**Vereiste** `hermes_cli`-modules (install faalt anders): `model_runtime_config`, `usage_snapshot`, `status_bar_cost`.

**Optioneel** — ontbrekend bestand → warning, geen abort.

**Runtime-patches** (Tier B, niet in Tier A):

| Module | Functie |
|--------|---------|
| `overlay/hermes_cli/cli_fork_patch.py` | Statusbalk-kosten, layout, throughput-hooks op `HermesCLI` |
| `overlay/hermes_cli/cli_command_patches.py` | `/cost` en `/tps` via `process_command` |
| `overlay/hermes_cli/cli_cost_command.py` | `/cost`-handler |
| `overlay/hermes_cli/cli_tps_command.py` | `/tps`-handler (`display.show_status_bar_tps`) |
| `overlay/hermes_cli/cli_tps_stream_hooks.py` | CLI stream tok/s (`_record_stream_tps_delta`, `_freeze_stream_tps_segment`) |
| `overlay/agent/agent_throughput_fork_patch.py` | Agent stream/finalize tok/s: `AIAgent.__init__` koppelt compressor via `_fork_throughput_agent` op instantie; `_fire_stream_delta` + `ContextCompressor.update_from_response` (fouten → debug-log) |
| `overlay/agent/pricing_fork_patch.py` | Google Gemini-catalogus in `usage_pricing` |
| `overlay/agent/google_gemini_pricing.py` | Prijstabel Gemini 3.x |
| `overlay/hermes_cli/models_fork_patch.py` | Startup model-catalog guard |
| `overlay/hermes_cli/auth_fork_patch.py` | `read_auth_json` (BOM), `sync_root_active_provider`, `_read_shared_nous_state` (BOM) |
| `overlay/tui_gateway/gateway_config_fork_patch.py` | Gateway `/cost`, `cost_bar_mode`, `/tps`, usage snapshot |
| `overlay/hermes_cli/argparse_fork_patch.py` | `profile use` flags + `config get` |
| `overlay/hermes_cli/cli_profile_fork_patch.py` | `execute_profile_switch`, `_parse_profile_switch_intent` |
| `overlay/hermes_cli/config_fork_patch.py` | `get_config_value`, `config get` handler |
| `overlay/hermes_cli/doctor_fork_patch.py` | `_check_windows_split_home_config` |
| `overlay/hermes_cli/tools_config_fork_patch.py` | `platform_toolsets.cli` lege-lijst guard, `_user_customized`, `expand_cli_toolset_arg` (MCP-sentinel) |
| `overlay/hermes_cli/clipboard_fork_patch.py` | `get_clipboard_text` / `set_clipboard_text` (Windows plain-text clipboard) |
| `overlay/hermes_cli/profiles_fork_patch.py` | `iter_orphan_profile_wrappers`, `remove_orphan_profile_wrappers` |
| `overlay/hermes_cli/main_fork_patch.py` | `_wait_for_interpreter_venv_ready` (update/desktop venv guard) |
| `overlay/tools/process_registry_fork_patch.py` | `_pty_spawn_argv` (Windows PTY spawn) |
| `overlay/cli_fork_patch.py` | `cli._wrap_bron_citations_for_display` (RAG bron-citaties) |
| `overlay/ui-tui/src/components/appChrome.tsx` | Status-rule cost/throughput layout (`resolveStatusRuleLayout`) |
| `overlay/hermes_cli/auth_fork_patch.py` | Auth/split-home runtime patches |
| `overlay/tui_gateway/gateway_config_fork_patch.py` | Gateway config cache / split-home |
| `overlay/agent/prompt_builder_fork_patch.py` | Legal runtime path block op `agent.prompt_builder` |

**Start:**

- [`overlay/bootstrap_startup.py`](../overlay/bootstrap_startup.py) — `PYTHONSTARTUP` (fouten gelogd, interpreter blijft starten).
- [`windows/scripts/Invoke-HermesOverlayBootstrap.ps1`](../windows/scripts/Invoke-HermesOverlayBootstrap.ps1) — zet `PYTHONSTARTUP`.
- [`windows/scripts/launch_hermes.ps1`](../windows/scripts/launch_hermes.ps1) — bootstrap vóór chat.

**Tests:** `pytest tests/overlay/` (overlay unit, gemockt); `tests/conftest.py` roept `install()` vóór collectie. Fork gates: `tests/audits/test_nous_overlay_fork_gates_e2e_harness.py`, `tests/overlay/test_argparse_fork_patch.py`, `tests/windows/test_toolset_domain_e2e_runtime.py`. Toolset dashboard (Tier A upstream): `tests/hermes_cli/test_dashboard_admin_endpoints.py`, fork MCP-sentinel `tests/overlay/test_tools_config_fork_patch.py`, E2E `audits/RUN_TOOLSET_DASHBOARD_E2E.bat`. Agent-throughput: `tests/overlay/test_agent_throughput_fork_patch.py`.

**Toolset dashboard UI/API/routes:** upstream Tier A (`web/src/components/ToolsetConfigDrawer.tsx`, `web/src/lib/api.ts`, `hermes_cli/web_server.py`, `hermes_cli/main.py`). Overlay web bevat alleen institutioneel fork-specifiek (themes, analytics, enz.).

**Tier B script guards:**

- `windows/scripts/sync_profile_toolsets_from_manifest.py` — neutraliseert eigen `--profile`/`-p` in `sys.argv` vóór `overlay.bootstrap.install()` (voorkomt `hermes_cli.main._apply_profile_override` op script-flags).
- `scripts/run_hermes_cli_with_overlay.py` — canonieke CLI-entry na bootstrap (o.a. `hermes config get`).
- `windows/scripts/sync_profile_memories.ps1` — verwijdert stale legal-domain USER-secties vóór merge; dedup via `invoke_deduplicate_memories.ps1 -HermesRoot $root`.

## UI-build (Tier B, geen Tier A-src-leak)

```powershell
powershell -File windows/scripts/build_fork_ui_assets.ps1
```

Kopieert overlay → `web/src` / `ui-tui/src`, bouwt assets, herstelt Tier A `src` altijd (`git checkout`) — ook bij build-fail.

Bron-sync: [`Invoke-CopyHermesOverlaySources.ps1`](../windows/scripts/Invoke-CopyHermesOverlaySources.ps1) (alleen als overlay nieuwer is).

## Drift (strict)

**SSOT onderhoud:** [NOUS_DRIFT_MAINTENANCE.md](NOUS_DRIFT_MAINTENANCE.md) · snapshot: [NOUS_DRIFT_BASELINE.md](NOUS_DRIFT_BASELINE.md).

```cmd
windows\SYNC_NOUS_DRIFT_CATCHUP.bat
```

Handmatig: `Test-NousTreeIdentical.ps1` → `Invoke-RestoreNousTierA.ps1` of targeted checkout → `Export-NousDriftBaseline.ps1`. Geen `SYNC_NOUS -Yes` voor routine drift op deze fork.

## E2E (institutioneel)

| Audit | Commando |
|-------|----------|
| Sync + drift | `windows\audits\RUN_SYNC_NOUS_E2E.bat` |
| Overlay runtime + cost + drift | `audits\RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E.bat` |
| Overlay runtime wiring (P0–P5) | `audits\RUN_NOUS_OVERLAY_RUNTIME_E2E.bat` — bootstrap idempotentie, agent/CLI TPS hooks, `/tps`+`/cost`, tier-A guard, overlay pytest-subset |
| Fork gates (Tier B scripts) | `audits\RUN_NOUS_OVERLAY_FORK_GATES_E2E.bat` — argv `--profile` sanitizer vóór bootstrap, `config get`, toolset `--check` skip `_user_customized`, legal USER stale-strip + dedup `-HermesRoot` |
| Toolset dashboard (Tier A) | `audits\RUN_TOOLSET_DASHBOARD_E2E.bat` — Tier A routes/CLI/UI + fork MCP-sentinel overlay, pytest subset (9/9) |
| Afwerking (dedup/trust/bootstrap) | `audits\RUN_NOUS_OVERLAY_AFWERKING_E2E.bat` — regel-§ dedup, `RUN_AUDITS` trust preflight, `SYNC_TRUST_RUNTIME` retry, `collect_env_sync_keys` bootstrap |
| Throughput tok/s (overlay) | `audits\RUN_STATUS_BAR_THROUGHPUT_E2E.bat` |
| Prompt-timer (overlay) | `audits\RUN_PROMPT_TIMER_DISPLAY_E2E.bat` |
| Klassieke CLI statusbalk | `windows\audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat` |
| Gecombineerd | `windows\audits\RUN_AUDITS.bat -IncludeNousOverlayInstitutionalE2E -IncludeSyncNousE2E` |
| Volledige poort | `windows\audits\RUN_AUDITS.bat -IncludeAllE2E` (incl. overlay + throughput + **fork gates** E2E) |

**CI:** `.github/workflows/fork-windows-institutional.yml` — upstream fetch, drift gate, 14-fixes E2E, pytest-audit-env, tier-a-cli guard, overlay E2E, TUI-build + drift. Wekelijks: `fork-windows-audits-nightly.yml` (`RUN_AUDITS -IncludeAllE2E`).

**Tier A guard:** `python scripts/verify_institutional_guard.py --check-tier-a-cli` · staged tier-A edits: `windows/scripts/check_fork_tier_a_edits.py --staged --warn` (pre-commit) — nieuw fork-gedrag via `overlay/hermes_cli/*_fork_patch.py`, niet direct `hermes_cli/*.py` wijzigen.

**pytest (Windows):** `pyproject.toml` = upstream `signal`; fork gate/upstream runners via `Invoke-HermesAuditPytest` / manifest (`windows/tests/PYTEST_POLICY.md`).

**doctor_fork_patch:** split-home **+** profile global-blocks strip (`strip_profile_global_config_blocks.py`, doctor `--fix`).

Preflight: `HERMES_HOME=%LOCALAPPDATA%\hermes` (niet `profiles\legal`).

## Verify / smoke (Python)

```bat
python scripts\verify_usage_cost_bar.py --verify
python scripts\status_bar_cost_classic_cli_smoke.py
python scripts\status_bar_cost_classic_cli_live_smoke.py
```

## Extras (RAG)

- [`overlay/requirements-fork-extras.txt`](../overlay/requirements-fork-extras.txt)
- [`windows/scripts/install_rag_extras.ps1`](../windows/scripts/install_rag_extras.ps1)

## Merge-beleid

[`windows/merge_upstream_fork.ps1`](../windows/merge_upstream_fork.ps1): Tier B `keepOurs`, Tier A default `theirs`.

## Remotes

| Remote | Rol |
|--------|-----|
| `upstream` | NousResearch/hermes-agent |
| `origin` | J80-droid/hermes-agent-windows-nl (Tier B + merge commits) |

`hermes update` trekt **origin**; Nous-merge via `SYNC_NOUS` / `upstream_sync.ps1`.

## Cadence

| Ritueel | Frequentie | Commando |
|---------|------------|----------|
| Drift catch-up | na upstream-push / wekelijks | `windows\SYNC_NOUS_DRIFT_CATCHUP.bat` |
| Nous merge (gecontroleerd) | max. 1–2 weken | `windows\SYNC_NOUS.bat` (niet `-Yes` voor routine drift) |
| Drift baseline | na catch-up | `Export-NousDriftBaseline.ps1` (in catch-up) |
| Merge-beleid | bij conflicts | Tier A `theirs`, Tier B `keepOurs` — `merge_upstream_fork.ps1` |
| UI-build na Web/TUI-pull | na sync | `build_fork_ui_assets.ps1` + drift-check |

Max. 1–2 weken achter op `upstream/main`. Zie [NOUS_DRIFT_MAINTENANCE.md](NOUS_DRIFT_MAINTENANCE.md) · [UPSTREAM_SYNC.md](../windows/UPSTREAM_SYNC.md).

`UPDATE_HERMES.bat` voert standaard drift gate + auto catch-up uit; `-StrictNousSync` = hard fail bij resterende drift.

## Plugins / optionele overlay-modules

**ADR — waarom `plugin.yaml` i.p.v. bootstrap plugin-load:** `plugins/j80-windows-nl` is een manifest/registry voor slash-dispatch (`/cost`, `/tps`). Handlers leven in `overlay/hermes_cli/` en worden via `cli_command_patches` geïnjecteerd. Bootstrap laadt alleen runtime-patches uit `manifest.yaml`; extra plugin-load zou Tier A-imports of dubbele registratie riskeren.

- **`plugins/j80-windows-nl`:** in `overlay/manifest.yaml` maar **niet** geladen door `bootstrap.py`; slash-commands via overlay CLI-patches. E2E: handlers importeerbaar (`RunAudits14FixesE2E` E11).
- **Bootstrap `hermes_cli` (overlay):** `filesystem_sandbox`, `hardware_backend`, `config_snapshot` — geladen via `_OVERLAY_HERMES_CLI_MODULES`; file-tools wiring via `overlay/tools/file_tools_fork_patch.py`.
- **Lazy overlay `hermes_cli`:** `model_catalog_guard` (via `models_fork_patch`), `model_list_ui`, `skills_hub_init`, `win32_console` — niet in `_OVERLAY_HERMES_CLI_MODULES`; unit smoke: `tests/overlay/test_lazy_overlay_imports.py`.

**Overlay bron-sync:** `Invoke-CopyHermesOverlaySources.ps1` kopieert overlay → Tier A `src` alleen tijdens UI-build (met restore). `Copy-ForkAdditionToOverlay` (in `Invoke-RestoreNousTierA`) kopieert fork-only **toevoegingen** naar overlay alleen als het overlay-bestand nog ontbreekt — handmatige sync bij wijzigingen vereist.

`windows/scripts/collect_env_sync_keys.py` roept `overlay.bootstrap.install()` aan vóór `profile_model_inheritance.root_config_path()`.
