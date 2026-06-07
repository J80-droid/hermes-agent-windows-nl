# NOUS drift onderhoud (SSOT)

Technische referentie voor tier-A sync. **Als gebruiker hoef je dit niet te lezen.**

## Jouw workflow (2 scripts)

| Wat | Script | Wat het doet |
|-----|--------|----------------|
| **Dagelijks starten** | `start_hermes.bat` (repo-root) | Start Hermes; haalt `origin` op als die achterloopt + post-pull onderhoud |
| **Nous/upstream bijwerken** | `windows\UPDATE_HERMES.bat` | Merge upstream, deps, trust/RAG, **tier-A drift auto-fix + commit** |

Daarna opnieuw `start_hermes.bat` (of `/new` in chat). **Geen** aparte drift-scripts nodig.

```cmd
windows\UPDATE_HERMES.bat
start_hermes.bat
```

Optioneel zonder pauze: `windows\UPDATE_HERMES_YES.bat` (zelfde keten).

### Wat UPDATE_HERMES automatisch doet (drift)

Na een geslaagde upstream-update:

1. `git fetch upstream` + drift-check t.o.v. `upstream/main`
2. Bij drift → tier-A sync (fork-intentional `gateway_windows.py` behouden)
3. Fork pytest gate + baseline-export
4. **Commit** van drift-fix (tenzij `-SkipNousDriftCommit`)

Mislukt iets → update stopt met foutcode (geen stille waarschuwing).

### Start vs update

| | `start_hermes.bat` | `UPDATE_HERMES.bat` |
|--|-------------------|---------------------|
| **Bron** | `git pull` van **origin** (jouw fork) | Merge **upstream** (Nous) |
| **Tier-A drift** | Niet nodig (origin is al gesynced) | Auto catch-up |
| **Wanneer** | Elke sessie | Periodiek / bij grote Nous-achterstand |

---

## Doel (architectuur)

| Tier | Drift-gate | Fork-gedrag |
|------|------------|-------------|
| **A** | `HEAD` ≈ `upstream/main` | Alleen allowlist in `HermesNousTierPaths.ps1` |
| **B** | Geen upstream-vergelijking | `overlay/`, `windows/`, tests, … |

## Interne scripts (maintainer/CI — niet dagelijks)

| Script | Rol |
|--------|-----|
| `Invoke-HermesNousDriftGateWithCatchUp.ps1` | Aangeroepen door `UPDATE_HERMES` |
| `SYNC_NOUS_DRIFT_CATCHUP.bat` | Zelfde keten los (debug/CI) |
| `Test-NousTreeIdentical.ps1` | CI strict gate |
| `Invoke-HermesPostGateWorktreeReset.ps1` | Na `RUN_PRODUCTION_GATE` |

**Taboe:** `SYNC_NOUS.bat -Yes` voor routine drift op deze fork.

Zie [`NOUS_OVERLAY_ARCHITECTURE.md`](NOUS_OVERLAY_ARCHITECTURE.md) · [`PYTEST_POLICY.md`](../windows/tests/PYTEST_POLICY.md) · [`FORK_MERGE_POLICY.md`](FORK_MERGE_POLICY.md) (merge-conflicten in upstream-tests voorkomen).
