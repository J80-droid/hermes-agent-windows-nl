# Nous overlay-architectuur (100% intact Tier A)

## Regels

1. **Tier A (Nous)** — Bestanden die in `upstream/main` bestaan onder `agent/`, `cli.py`, `hermes_cli/`, `web/`, `ui-tui/`, enz. blijven **identiek** aan upstream na `SYNC_NOUS`.
2. **Tier B (overlay)** — `overlay/`, `windows/`, `scripts/rag_pipeline/`, skills, runtime `~/.hermes/`.

## Sync-keten

```cmd
windows\SYNC_NOUS.bat
windows\SYNC_NOUS.bat -Yes
```

Fasen: preflight → merge (`upstream_sync.ps1`) → `Invoke-ApplyHermesOverlay` → post-merge → `Test-NousTreeIdentical.ps1`.

`UPDATE_HERMES.bat` blijft dagelijkse entry; gebruik `SYNC_NOUS` wanneer je expliciet Nous + overlay wilt valideren.

## Bootstrap

- [`overlay/bootstrap.py`](../overlay/bootstrap.py) registreert `hermes_cli.*` modules uit [`overlay/hermes_cli/`](../overlay/hermes_cli/).
- [`windows/scripts/Invoke-HermesOverlayBootstrap.ps1`](../windows/scripts/Invoke-HermesOverlayBootstrap.ps1) zet `PYTHONSTARTUP=overlay/bootstrap_startup.py`.
- [`windows/scripts/launch_hermes.ps1`](../windows/scripts/launch_hermes.ps1) roept bootstrap aan vóór chat.

## Drift (strict)

```powershell
powershell -File windows/scripts/Invoke-RestoreNousTierA.ps1
powershell -File windows/scripts/Test-NousTreeIdentical.ps1
powershell -File windows/scripts/Export-NousDriftBaseline.ps1
```

E2E: `windows\audits\RUN_SYNC_NOUS_E2E.bat` of `RUN_AUDITS -IncludeSyncNousE2E -SkipHermesPreflight`.

Baseline: [NOUS_DRIFT_BASELINE.md](NOUS_DRIFT_BASELINE.md).

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
