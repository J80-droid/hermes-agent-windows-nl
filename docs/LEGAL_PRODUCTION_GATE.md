# Legal domein — productie-poort

Operationele matrix voor institutioneel legal-domein (fork). Volledige architectuur: [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md).

## Snelle checks

| Doel | Script | Exit 0 |
|------|--------|--------|
| Dagelijkse runtime | `windows\VERIFY_LEGAL_RUNTIME.bat` | SOUL meta + parity + `domains.yaml` (warn zonder strict) |
| Snelle repo-E2E (geen RAG) | `audits\RUN_LEGAL_PRODUCTION_E2E.bat` | 17 harness-stappen + pytest-contract |
| Volledige poort | `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat` | 12 stappen |
| Strict bronnen | `RUN_LEGAL_DOMAIN_E2E.bat -StrictSources` | Bronmap verplicht |
| Lens sync toepassen | `RUN_LEGAL_DOMAIN_E2E.bat -ApplyLensSync` | `--all` i.p.v. dry-run |
| Legal skills | `audits\RUN_LEGAL_SKILLS_ROOKTEST.bat` | pytest skills/legal |
| Audits bundle | `RUN_AUDITS.bat -IncludeLegalDomainE2E` | Legal E2E in keten |

## Wanneer welke rooktest

| Situatie | Gebruik |
|----------|---------|
| Na skill-wijziging onder `skills/legal/` | `RUN_LEGAL_SKILLS_ROOKTEST.bat` + `RUN_REPO_HYGIENE_E2E.bat` |
| Na taxonomie/SOUL/deploy | `VERIFY_LEGAL_RUNTIME.bat` of `RUN_LEGAL_DOMAIN_E2E.bat` |
| Na ingest | `show_legal_ingest_dashboard.ps1` + stap 12 E2E (search rooktest) |
| Profielwissel + legal | `RUN_PROFILE_SWITCH_E2E.bat` daarna legal E2E |

## Gecombineerde release-gate (lokaal)

1. `UPDATE_HERMES.bat` (of pull + soul deploy)
2. `VERIFY_LEGAL_RUNTIME.bat` met `set HERMES_LEGAL_VERIFY_STRICT=1`
3. `RUN_LEGAL_DOMAIN_E2E.bat -StrictSources`
4. `RUN_PROFILE_SWITCH_E2E.bat` (legal ↔ core)
5. Chat smoke: profiel `legal`, vraag *“Hoe ziet het team van agents eruit?”* → lenzen; of `/legal-architectuur`

## User-data (P0)

| Item | Pad | Actie |
|------|-----|--------|
| domains.yaml | `%USERPROFILE%\data\domains.yaml` | `legal` + `lancedb-legal` (voorbeeld: `docs/domains.yaml.example`) |
| Bronnen | `%USERPROFILE%\data\raw_source_files\04_Legal_Corporate\` | `MIGRATE_LEGAL_LAYOUT.bat` dry-run → `-Apply` |
| MATTERS | `profiles\legal\LEGAL_ACTIVE_MATTERS.md` | Auto-seed via `ensure_legal_active_matters.ps1` |
| Trust | `profiles\legal\memories\USER.md` | `SYNC_TRUST_RUNTIME.bat` |

Diagnose: `windows\scripts\which_hermes_repo.ps1`

## CI

GitHub `fork-windows-institutional.yml` draait hardening (legal skills pytest), **geen** volledige `RUN_LEGAL_DOMAIN_E2E` (vereist Windows runtime). Release: run legal E2E lokaal vóór push.

## Environment

| Variabele | Betekenis |
|-----------|-----------|
| `HERMES_LEGAL_VERIFY_STRICT=1` | verify/E2E fail op waarschuwingen |
| `HERMES_SKIP_LEGAL_LENS_SYNC=1` | Lens sync overslaan |
| `HERMES_LEGAL_PHASE_3B=1` | Geen warn op profiel `klokkenluiders` |
| `HERMES_UPSTREAM_BEHIND_WARN` | Drempel upstream-banner (default 10) |

## Unit tests (na codewijziging)

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File windows\tests\LegalDomainE2E.Unit.Tests.ps1
pytest tests/windows/test_legal_domain_e2e_unit.py tests/audits/test_legal_production_e2e_harness.py tests/scripts/test_verify_legal_lens_parity.py tests/scripts/test_legal_lens_from_path.py tests/hermes_cli/test_legal_architecture_brief.py -q
```

`RUN_AUDITS.bat -IncludeLegalDomainE2E` draait eerst de geïsoleerde unit (gemockte paden), daarna de volledige `RUN_LEGAL_DOMAIN_E2E.bat`.

Renderer rooktest (geen legal-domein): `pytest tests/scripts/test_score_institutional_render.py -q` — zie [templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md).

## Zie ook

- [LEGAL_ROLLOUT_CHECKLIST.md](LEGAL_ROLLOUT_CHECKLIST.md)
- [../audits/LEGAL_PRODUCTION_E2E_README.md](../audits/LEGAL_PRODUCTION_E2E_README.md)
- [INSTITUTIONAL_OPERATIONS.md](INSTITUTIONAL_OPERATIONS.md)
- [PROFILE_SWITCH.md](PROFILE_SWITCH.md)
