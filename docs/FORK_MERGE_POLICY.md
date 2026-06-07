# Fork merge-beleid (Windows NL)

Voorkomt terugkerende merge-conflicten in upstream-owned testbestanden (zoals `tests/hermes_cli/test_web_server.py`).

Zie ook [`NOUS_DRIFT_MAINTENANCE.md`](NOUS_DRIFT_MAINTENANCE.md) (tier-A drift) en [`../windows/tests/PYTEST_POLICY.md`](../windows/tests/PYTEST_POLICY.md).

## Cadans

| Frequentie | Actie |
|------------|--------|
| **Bij behind ≥ 5** (default drempel) | `windows\UPDATE_HERMES.bat -Yes` wanneer geen actieve chat/gateway |
| **Waarschuwing bij start** | `start_hermes.bat` / sessie-onderhoud — **geen** auto-merge, geen Taakplanner |
| **Upstream parity** | Zit in UPDATE finalize — `ReportOnly` + `new_failures_count` |
| **Vóór release** | `windows\UPDATE_HERMES.bat -Release` of los `RUN_PRODUCTION_GATE.bat` |

Bij honderden upstream-commits/dag: niet weken wachten. Drempel aanpassen: `HERMES_UPSTREAM_BEHIND_WARN`.

**Eén commando dekt:** preflight, merge, RAG/trust, drift catch-up + fork gate, upstream rapport, push naar `origin/main`. Handmatig alleen bij merge-conflict of `-SkipPush`.

## Waar nieuwe fork-tests horen

| Locatie | Gebruik |
|---------|---------|
| `tests/overlay/` | Gedrag via overlay-patches (voorkeur) |
| `tests/windows/` | Windows-scripts, gateway, smoke |
| `windows/tests/` | Gate-manifesten, harness |

**Niet** nieuwe bestanden of fork-only asserts toevoegen onder `tests/hermes_cli/` — dat is upstream-owned en leidt bij merge tot conflicten.

## Legacy-uitzonderingen

Lijst: [`windows/tests/fork_hermes_cli_test_exceptions.txt`](../windows/tests/fork_hermes_cli_test_exceptions.txt).

**Status (2026-06):** leeg — alle 35 fork-only `tests/hermes_cli/`-bestanden zijn gemigreerd naar `tests/overlay/` of `tests/windows/`. `tests/hermes_cli/` is upstream-pariteit (`git diff upstream/main -- tests/hermes_cli/` → leeg).

**Geen nieuwe paden** toevoegen aan de exceptions-lijst; nieuwe fork-tests horen in `tests/overlay/` of `tests/windows/`.

Voorbeeld migratie: `test_get_assistant_display_settings` → `tests/overlay/test_web_server_assistant_display.py` (fork API `/api/display/assistant`). Volledige backlog: [`FORK_TEST_MIGRATION_BACKLOG.md`](FORK_TEST_MIGRATION_BACKLOG.md).

E2E-verificatie na migratie: `audits\RUN_FORK_HERMES_CLI_TEST_MIGRATION_E2E.bat`.

## Automatische check

Script: `windows/scripts/check_fork_hermes_cli_tests.py`

| Modus | Wanneer | Gedrag |
|-------|---------|--------|
| `--pre-merge` | Preflight in `UPDATE_HERMES` (na fetch, als achter op upstream) | **Waarschuwing**: bestanden die t.o.v. `upstream/main` wijzigen = conflict-risico |
| `--staged` | Optioneel strict / pre-commit | **Blokkeert** staged toevoegingen in `tests/hermes_cli/` buiten de exceptions-lijst |

PowerShell-wrapper: `windows/scripts/Test-ForkHermesCliTestHygiene.ps1`

Om staged-violations hard te blokkeren vóór merge: `HERMES_FORK_CLI_TEST_STRICT=1` of `-StrictForkCliTests` op de hygiene-test.

## Bij merge-conflict in tests

1. **Upstream-test behouden** waar het upstream-gedrag dekt.
2. **Fork-gedrag** verplaatsen naar `tests/overlay/` of bestaand overlay-testbestand uitbreiden.
3. **Niet** beide testblokken permanent in hetzelfde upstream-bestand laten staan tenzij het letterlijk dezelfde upstream-regels zijn.
4. Na fix: `UPDATE_HERMES.bat` opnieuw (fase 2/3).

## Conflictzones (historisch)

`pyproject.toml`, `uv.lock`, `tests/hermes_cli/test_web_server.py`, `scripts/run_tests.sh` — bij grote merges eerst deze controleren.
