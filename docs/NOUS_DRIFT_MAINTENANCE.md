# NOUS drift onderhoud (SSOT)

**Single source of truth** voor tier-A drift na `upstream/main`-pushes. De snapshot in [`NOUS_DRIFT_BASELINE.md`](NOUS_DRIFT_BASELINE.md) wordt alleen gegenereerd; dit document blijft stabiel.

Zie ook: [`NOUS_OVERLAY_ARCHITECTURE.md`](NOUS_OVERLAY_ARCHITECTURE.md) · [`windows/tests/PYTEST_POLICY.md`](../windows/tests/PYTEST_POLICY.md).

## Doel

| Tier | Drift-gate | Fork-gedrag |
|------|------------|-------------|
| **A** | `HEAD` ≈ `upstream/main` (0× must-upstream) | Alleen allowlist in `HermesNousTierPaths.ps1` |
| **B** | Geen upstream-vergelijking | `overlay/`, `windows/`, tests, … |

## Geautomatiseerde keten (standaard)

| Entry | Wanneer | Gedrag |
|-------|---------|--------|
| **`UPDATE_HERMES.bat`** | Na elke update | Drift gate + **auto catch-up** (mislukt = exit 1) |
| **`SYNC_NOUS.bat` (Full)** | Nous-merge | Zelfde gate + catch-up; `-Yes` commit catch-up |
| **`SYNC_NOUS_DRIFT_CATCHUP.bat`** | Handmatig / CI-lokaal | Volledige catch-up keten |
| **`RUN_PRODUCTION_GATE.bat`** | Na productie-poort | `Invoke-HermesPostGateWorktreeReset.ps1` |

Flags `UPDATE_HERMES.bat`: `-SkipNousDriftCatchUp` (alleen detectie), `-CommitNousDrift`, `-StrictNousSync`.

```cmd
windows\SYNC_NOUS_DRIFT_CATCHUP.bat
```

Keten: `git fetch upstream` → drift-report → targeted checkout (≤15 paden) of `Invoke-RestoreNousTierA` → **fork-intentional auto** → `RUN_PYTEST_FORK_GATE` → `Export-NousDriftBaseline` → optioneel `-Commit`.

## Handmatige stappen (zelfde policy)

```powershell
git fetch upstream
powershell -NoProfile -File windows/scripts/Test-NousTreeIdentical.ps1
# bij FAIL — klein:
git checkout upstream/main -- <pad1> <pad2> ...
# bij FAIL — groot:
powershell -NoProfile -File windows/scripts/Invoke-RestoreNousTierA.ps1
# fork-intentional terug (automatisch in restore + catch-up script):
#   gateway_windows.py uit HEAD — zie HermesNousTierAForkIntentional
windows\tests\RUN_PYTEST_FORK_GATE.bat
powershell -NoProfile -File windows/scripts/Export-NousDriftBaseline.ps1
git add -A && git commit -m "chore(nous): sync tier-A to upstream/main"
```

## Taboe

**Geen** `SYNC_NOUS.bat -Yes` voor routine drift-herstel op deze fork — overschrijft fork-intentional deltas (o.a. conda `VIRTUAL_ENV` in `hermes_cli/gateway_windows.py`).

`SYNC_NOUS.bat` (zonder `-Yes`) blijft voor gecontroleerde Nous-merge met prompts.

## Na productie-poort

Tier-A postflight **staged** upstream-bestanden. `git restore .` volstaat niet.

```powershell
powershell -NoProfile -File windows/scripts/Invoke-HermesPostGateWorktreeReset.ps1
```

Automatisch aan het einde van `RUN_PRODUCTION_GATE.bat`.

## Alleen detectie (opt-out)

`UPDATE_HERMES.bat -SkipNousDriftCatchUp` — drift-check zonder auto-fix (niet aanbevolen).

`Test-NousTreeIdentical.ps1` — strict gate voor CI (`fork-windows-institutional.yml`).

## Scripts (windows/scripts/)

| Script | Rol |
|--------|-----|
| `HermesNousDrift.ps1` | Gedeelde drift-logica + `Invoke-HermesNousTierADriftCatchUp` |
| `Invoke-HermesNousDriftGateWithCatchUp.ps1` | Detect + auto catch-up (UPDATE_HERMES, SYNC_NOUS) |
| `Invoke-SyncNousDriftCatchUp.ps1` | Catch-up alleen (CLI) |
| `Test-NousTreeIdentical.ps1` | Strict gate (CI) |
| `Invoke-RestoreNousTierA.ps1` | Volledige tier-A → upstream + fork-intentional auto |
| `Invoke-HermesPostGateWorktreeReset.ps1` | `git reset --hard HEAD` na staged postflight |
| `Export-NousDriftBaseline.ps1` | Baseline-snapshot |

## Cadans

| Wanneer | Actie |
|---------|--------|
| Na `git fetch` / upstream-merge | `SYNC_NOUS_DRIFT_CATCHUP.bat` of catch-up `.ps1` |
| Vóór release | Drift 0 + `RUN_PRODUCTION_GATE.bat` |
| Wekelijks | `Test-NousTreeIdentical` + upstream `RUN_PYTEST_UPSTREAM -ReportOnly` |
