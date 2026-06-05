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
| `overlay/hermes_cli/cli_command_patches.py` | `/cost` via `process_command` |
| `overlay/hermes_cli/cli_cost_command.py` | `/cost`-handler |
| `overlay/agent/pricing_fork_patch.py` | Google Gemini-catalogus in `usage_pricing` |
| `overlay/agent/google_gemini_pricing.py` | Prijstabel Gemini 3.x |
| `overlay/hermes_cli/models_fork_patch.py` | Startup model-catalog guard |

**Start:**

- [`overlay/bootstrap_startup.py`](../overlay/bootstrap_startup.py) — `PYTHONSTARTUP` (fouten gelogd, interpreter blijft starten).
- [`windows/scripts/Invoke-HermesOverlayBootstrap.ps1`](../windows/scripts/Invoke-HermesOverlayBootstrap.ps1) — zet `PYTHONSTARTUP`.
- [`windows/scripts/launch_hermes.ps1`](../windows/scripts/launch_hermes.ps1) — bootstrap vóór chat.

**Tests:** `pytest tests/overlay/test_bootstrap.py` (unit, gemockt); `tests/conftest.py` roept `install()` vóór collectie.

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
| Klassieke CLI statusbalk | `windows\audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat` |
| Gecombineerd | `windows\audits\RUN_AUDITS.bat -IncludeSyncNousE2E -IncludeClassicCliStatusBarCostE2E` |

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

Max. 1–2 weken achter op `upstream/main`. Zie [UPSTREAM_SYNC.md](../windows/UPSTREAM_SYNC.md).
