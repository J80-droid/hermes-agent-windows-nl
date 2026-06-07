# Legal Production E2E (`audits/`)

E2E voor de **legal productie P0–P3** implementatie (slash, parity, verify, pytest-contract). Geen live LLM.

## Draaien

```bat
audits\RUN_LEGAL_PRODUCTION_E2E.bat
```

Of:

```bat
python audits\LegalProductionE2E.harness.py
```

## Scenario's (harness)

| Stap | Wat |
|------|-----|
| S1 | Repo-artefacten (scripts, docs, bats) |
| S2–S5 | `/legal-architectuur` registry + brief (legal/core) |
| S6–S7 | SOUL-template meta (core + legal) |
| S8–S9 | `verify_legal_lens_parity` template + `--all` (eventueel sync-repair) |
| S10–S11 | `sync_legal_lens` dry-run + `legal_lens_from_path` smoke |
| S12 | pytest legal contract bundle (5 modules) |
| S13 | `ensure_legal_active_matters.ps1` |
| S14–S16 | `sync_legal_soul_from_template`, core SOUL template, lens `--all` |
| S17 | `verify_legal_runtime.ps1` (`HERMES_LEGAL_VERIFY_STRICT=1`) |

## Unit tests (gemockt, geen live keten)

| Module | Bestand |
|--------|---------|
| Harness | `pytest tests/audits/test_legal_production_e2e_harness.py -q` |
| Parity CLI | `pytest tests/scripts/test_verify_legal_lens_parity.py -q` |
| Lens uit pad | `pytest tests/scripts/test_legal_lens_from_path.py -q` |
| Slash-brief | `pytest tests/overlay/test_legal_architecture_brief.py -q` |

Gecombineerd (zoals in CI/hardening-subset): zie stap S12 in de harness.

## Gerelateerd (zwaarder, runtime)

Volledige machine-poort met SOUL/bronnen/RAG: `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat` (12 stappen).

Legal skills pytest: `audits\RUN_LEGAL_SKILLS_ROOKTEST.bat`.

Operationele matrix: `docs\LEGAL_PRODUCTION_GATE.md`.
