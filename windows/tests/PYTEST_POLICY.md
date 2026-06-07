# Pytest policy (Windows fork)

Single source of truth for **which pytest runs block release** vs **diagnostics only**.

## Tiers

| Runner | Scope | Exit 0 required? | When |
|--------|--------|------------------|------|
| **`RUN_PYTEST_FORK_GATE.bat`** | Manifest `pytest_fork_gate.yaml` (~fork core) | **Yes** (hard gate) | Daily dev, preflight, CI, production gate |
| **`RUN_PYTEST_UPSTREAM.bat -ReportOnly`** | Full `tests/` (excl. integration/e2e markers) | No (always 0 with `-ReportOnly`) | After upstream merge, weekly parity |
| **`RUN_PYTEST_UPSTREAM.bat`** (no `-ReportOnly`) | Full `tests/` | Yes if used as gate | Not a release gate on Windows |
| **`RUN_PRODUCTION_GATE.bat`** | REBUILD_TUI → fork gate → `RUN_AUDITS -IncludeAllE2E -SkipPytest` | **Yes** | Before release (~35–45 min) |

Manifest path: [`pytest_fork_gate.yaml`](pytest_fork_gate.yaml). Loader: [`../scripts/load_pytest_fork_gate.py`](../scripts/load_pytest_fork_gate.py).

## Architecture

- **Tier A** `pyproject.toml` stays upstream (`--timeout-method=signal`).
- All fork runners clear `PYTEST_ADDOPTS` and force **`--timeout-method=thread`** via `Invoke-HermesAuditPytest` / `Get-HermesAuditPytestOverrideArgs` (30s default).
- **`RUN_PYTEST.ps1`** is a backward-compat shim: default → fork gate; `-Upstream` / `-ReportOnly` → upstream runner.

## Workflows

| Cadence | Command |
|---------|---------|
| Daily / after Python changes | `windows\tests\RUN_PYTEST_FORK_GATE.bat` |
| Preflight (in RUN_AUDITS) | Same fork gate (one step, replaces old overlay + profile subset) |
| Before release | `windows\audits\RUN_PRODUCTION_GATE.bat` |
| After upstream merge | `RUN_PYTEST_UPSTREAM.bat -ReportOnly` → check `pytest_upstream_summary.json` |
| Wiring / regressie (snel, ~30s) | `audits\RUN_PYTEST_FORK_GATE_E2E.bat` |
| Runner hardening (arg split, stderr exit) | `audits\RUN_PYTEST_RUNNER_HARDENING_E2E.bat` |

## E2E audit (wiring, geen volledige gate-run)

`audits\RUN_PYTEST_FORK_GATE_E2E.bat` valideert manifest, loader JSON, PowerShell runners, RUN_AUDITS preflight, production gate `-SkipPytest`, junit summary en overlay collect-only (11 stappen).

`audits\RUN_PYTEST_RUNNER_HARDENING_E2E.bat` valideert runner-hardening: `Get-HermesPytestArgsFromConfig`, gescheiden `--maxfail`/`--junitxml`, `Invoke-HermesAuditPytest` stderr-`Continue`, `$global:LASTEXITCODE` na `Tee-Object`, drift-baseline fork-intentional sectie (10 stappen).

## Upstream known failures

Na de eerste `RUN_PYTEST_UPSTREAM.bat -ReportOnly`, kopieer verwachte Windows-parity nodeids naar `pytest_upstream_known_fails.txt` (comments `#` toegestaan). Volgende runs tonen dan alleen **nieuwe** failures in `new_failures`.

**Let op maxfail=50:** upstream stopt alfabetisch vroeg (vaak in `tests/agent/`). Tests in `tests/tools/` (bijv. `test_credential_files.py` pad-separators op Windows) kunnen **buiten** het rapport vallen — los draaien via `Invoke-HermesAuditPytest` indien nodig. Geen fork-gate manifest-uitbreiding voor Linux-parity.

## E3 terminology (codebase audit)

- **E3 fork gate** = `RUN_PYTEST_FORK_GATE` (must be green).
- **E3 upstream parity** = `RUN_PYTEST_UPSTREAM -ReportOnly` (diagnostic; **Linux CI** is upstream truth).

## After upstream merge checklist

1. Run `RUN_PYTEST_FORK_GATE.bat` — fix any new manifest-path failures.
2. Run `RUN_PYTEST_UPSTREAM.bat -ReportOnly` — review summary JSON for **new** failures.
3. If fork behavior changed, extend `pytest_fork_gate.yaml` paths (not full `tests/` in CI).

## Explicitly NOT in fork gate

Tests marked `@pytest.mark.e2e` only — covered by E2E bats:

- `test_repo_hygiene_institutional_e2e.py` → `RUN_INSTITUTIONAL_HARDENING_E2E`
- `test_nous_overlay_fork_gates_e2e_harness_runs` → `RUN_NOUS_OVERLAY_FORK_GATES_E2E.bat`

## Postflight & worktree (tier-A)

`RUN_PRODUCTION_GATE` / `-IncludeAllE2E` run **tier-A postflight** (`Invoke-HermesTierAPostAuditClean -Phase Postflight`): upstream tier-A files are restored for the drift gate, then **`git checkout upstream/main -- …` stages those paths**. That is expected; it does **not** change `HEAD`.

| Symptoom | Oplossing |
|----------|-----------|
| `git status` toont **staged** tier-A na gate | `powershell -File windows\scripts\Invoke-HermesPostGateWorktreeReset.ps1` (of `git reset --hard HEAD`) |
| Alleen unstaged wijzigingen | `git restore .` |
| Volledige tier-A terug naar upstream op disk **en** committen | `Invoke-RestoreNousTierA.ps1` → fork `gateway_windows.py` behouden → commit |

`RUN_PRODUCTION_GATE.ps1` roept na afloop automatisch `Invoke-HermesPostGateWorktreeReset.ps1` aan als er staged tier-A staat.

**Niet gebruiken voor routine drift:** `SYNC_NOUS.bat -Yes` overschrijft fork-intentional wijzigingen (o.a. conda `VIRTUAL_ENV` in `gateway_windows.py`). Zie [NOUS_DRIFT_BASELINE.md](../../docs/NOUS_DRIFT_BASELINE.md#onderhoud-fork-windows).

## Related

- [`README.md`](README.md) — local runners
- [`docs/CODEBASE_AUDIT_EVIDENCE.md`](../../docs/CODEBASE_AUDIT_EVIDENCE.md) — E0–E3 tiers
- [`docs/INSTITUTIONAL_OPERATIONS.md`](../../docs/INSTITUTIONAL_OPERATIONS.md) — cheat sheet
