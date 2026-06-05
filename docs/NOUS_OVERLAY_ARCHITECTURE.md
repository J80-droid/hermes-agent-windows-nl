# Nous overlay-architectuur (100% intact Tier A)

## Regels

1. **Tier A (Nous)** — Bestanden die in `upstream/main` bestaan onder `agent/`, `cli.py`, `hermes_cli/`, `web/`, `ui-tui/`, enz. blijven **identiek** aan upstream na `SYNC_NOUS` (strict drift-gate).
2. **Tier B (overlay)** — `overlay/`, `windows/`, `scripts/`, tests, runtime `%LOCALAPPDATA%\hermes\`.

Fork-specifiek gedrag (statusbalk-kosten, `/cost`, Gemini-pricing, model-catalog guard) leeft in **Tier B** en wordt via bootstrap op Tier A geplakt — niet door `cli.py` of `hermes_cli/*.py` in Tier A te wijzigen.

## Sync-keten

```cmd
windows\SYNC_NOUS.bat
windows\SYNC_NOUS.bat -Yes
```

Fasen: preflight → merge (`upstream_sync.ps1`) → `Invoke-ApplyHermesOverlay` → post-merge → `Test-NousTreeIdentical.ps1` (strict).

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
| `overlay/hermes_cli/argparse_fork_patch.py` | `profile use` flags + `config get` subparser |
| `overlay/hermes_cli/cli_profile_fork_patch.py` | `execute_profile_switch`, `_parse_profile_switch_intent` |
| `overlay/hermes_cli/config_fork_patch.py` | `get_config_value`, `config get` handler |
| `overlay/hermes_cli/doctor_fork_patch.py` | `_check_windows_split_home_config` |
| `overlay/hermes_cli/tools_config_fork_patch.py` | Expliciet lege `platform_toolsets.cli: []` |
| `overlay/agent/prompt_builder_fork_patch.py` | Legal runtime path block op `agent.prompt_builder` |

**Start:**

- [`overlay/bootstrap_startup.py`](../overlay/bootstrap_startup.py) — `PYTHONSTARTUP` (fouten gelogd, interpreter blijft starten).
- [`windows/scripts/Invoke-HermesOverlayBootstrap.ps1`](../windows/scripts/Invoke-HermesOverlayBootstrap.ps1) — zet `PYTHONSTARTUP`.
- [`windows/scripts/launch_hermes.ps1`](../windows/scripts/launch_hermes.ps1) — bootstrap vóór chat.

**Tests:** `pytest tests/overlay/` (**112** unit tests, gemockt); `tests/conftest.py` roept `install()` vóór collectie. Agent-throughput: `tests/overlay/test_agent_throughput_fork_patch.py` (helpers + `apply_agent_throughput_fork_patch` met geïsoleerde stubs).

## UI-build (Tier B, geen Tier A-src-leak)

```powershell
powershell -File windows/scripts/build_fork_ui_assets.ps1
```

Kopieert overlay → `web/src` / `ui-tui/src`, bouwt assets, herstelt Tier A `src` altijd (`git checkout`) — ook bij build-fail.

Bron-sync: [`Invoke-CopyHermesOverlaySources.ps1`](../windows/scripts/Invoke-CopyHermesOverlaySources.ps1) (alleen als overlay nieuwer is).

## Drift (strict)

```powershell
powershell -File windows/scripts/Invoke-RestoreNousTierA.ps1
powershell -File windows/scripts/Test-NousTreeIdentical.ps1
powershell -File windows/scripts/Export-NousDriftBaseline.ps1
```

Baseline: [NOUS_DRIFT_BASELINE.md](NOUS_DRIFT_BASELINE.md).

## E2E (institutioneel)

| Audit | Commando |
|-------|----------|
| Sync + drift | `windows\audits\RUN_SYNC_NOUS_E2E.bat` |
| Overlay runtime + cost + drift | `audits\RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E.bat` |
| Overlay runtime wiring (P0–P5) | `audits\RUN_NOUS_OVERLAY_RUNTIME_E2E.bat` — bootstrap idempotentie, agent/CLI TPS hooks, `/tps`+`/cost`, tier-A guard, overlay pytest-subset |
| Throughput tok/s (overlay) | `audits\RUN_STATUS_BAR_THROUGHPUT_E2E.bat` |
| Prompt-timer (overlay) | `audits\RUN_PROMPT_TIMER_DISPLAY_E2E.bat` |
| Klassieke CLI statusbalk | `windows\audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat` |
| Gecombineerd | `windows\audits\RUN_AUDITS.bat -IncludeNousOverlayInstitutionalE2E -IncludeSyncNousE2E` |
| Volledige poort | `windows\audits\RUN_AUDITS.bat -IncludeAllE2E` (incl. overlay + throughput E2E) |

**CI:** `.github/workflows/fork-windows-institutional.yml` — drift gate, `pytest tests/overlay/`, institutional E2E, TUI-build + drift.

**Tier A guard:** `python scripts/verify_institutional_guard.py --check-tier-a-cli`

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
| Nous sync | max. 1–2 weken | `windows\SYNC_NOUS.bat` |
| Drift baseline | na elke sync/merge | `windows\scripts\Export-NousDriftBaseline.ps1` |
| Merge-beleid | bij conflicts | Tier A `theirs`, Tier B `keepOurs` — `windows\merge_upstream_fork.ps1` |
| UI-build na Web/TUI-pull | na sync | `build_fork_ui_assets.ps1` + `Test-NousTreeIdentical.ps1` |

Max. 1–2 weken achter op `upstream/main`. Zie [UPSTREAM_SYNC.md](../windows/UPSTREAM_SYNC.md) en [NOUS_DRIFT_BASELINE.md](NOUS_DRIFT_BASELINE.md).
