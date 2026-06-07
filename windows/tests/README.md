# Lokale pytest-runners (Windows)

Deze map is **niet** de upstream pytest-collectie. De echte tests staan in de repo-root: **`hermes-agent\tests\`**.

## Keuze: pytest en PSScriptAnalyzer gescheiden

**PSScriptAnalyzer** hoort **niet** standaard vóór elke pytest-run: pytest is al zwaar (duizenden tests), en PS-lint is een **andere concern** (alle `windows\*.ps1`). Je wilt tijdens Python-werk **snel** kunnen herhalen zonder module-installatie / analyse-overhead.

- **Volledige kwaliteitspoort** (PSSA + ruff + footguns + npm + ty): **`windows\audits\RUN_AUDITS.ps1`** — PSSA alleen als de module **al** geïnstalleerd is; anders **SKIP** (geen hang op PSGallery). Streng: **`RUN_AUDITS.ps1 -RequirePSScriptAnalyzer`**.
- **Alleen PowerShell onder `windows\`**: **`RUN_PSScriptAnalyzer.ps1`** (zelfde helper als audits)
- **Alleen Python-tests (fork gate)**: **`RUN_PYTEST_FORK_GATE.ps1`** — manifest SSOT; zie **[`PYTEST_POLICY.md`](PYTEST_POLICY.md)**
- **Upstream parity (diagnostiek)**: **`RUN_PYTEST_UPSTREAM.ps1 -ReportOnly`**
- **Backward compat shim**: **`RUN_PYTEST.ps1`** (default → fork gate; `-Upstream` → volledige suite)

## Pytest overlay shims (collection)

`overlay.bootstrap.install()` registreert o.a. `skills_hub_init`, `win32_console`, `expand_cli_toolset_arg`, clipboard-text, profiles orphan wrappers, `process_registry._pty_spawn_argv` en `cli._wrap_bron_citations_for_display`. Op Windows: `test_curses_arrow_keys` wordt overgeslagen zonder `_curses`.

## Toolset dashboard (Tier A + fork MCP-sentinel)

Snelle regressie (gemockt, geen live dashboard):

```powershell
python -m pytest tests/overlay/test_tools_config_fork_patch.py tests/hermes_cli/test_dashboard_admin_endpoints.py -q -k "toolset or post_setup or expand_cli or Toolset" -o addopts=--timeout=60 --timeout-method=thread
```

E2E harness: `audits\RUN_TOOLSET_DASHBOARD_E2E.bat` (9/9).

## Fork tests/hermes_cli/ migratie (upstream-pariteit)

Alle fork-only tests staan in `tests/overlay/` of `tests/windows/`; `tests/hermes_cli/` wijkt niet af van upstream.

| Check | Commando |
| ----- | -------- |
| Pre-merge hygiene | `python windows/scripts/check_fork_hermes_cli_tests.py --pre-merge --strict` |
| Staged guard (pre-commit) | `python windows/scripts/check_fork_hermes_cli_tests.py --staged` |
| E2E migratie | `audits\RUN_FORK_HERMES_CLI_TEST_MIGRATION_E2E.bat` |
| Unit guard | `pytest tests/windows/test_check_fork_hermes_cli_tests.py -q` |

Zie [`docs/FORK_MERGE_POLICY.md`](../../docs/FORK_MERGE_POLICY.md).

## Profielwissel (subset)

Snelle regressie zonder volledige suite:

```powershell
.\windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Of alleen pytest:

```powershell
python -m pytest tests/hermes_cli/test_apply_profile_override.py tests/overlay/test_profile_switch.py tests/hermes_cli/test_relaunch.py::TestRelaunchChatAfterProfileSwitch -q
```

## PowerShell unit tests (launch / dashboard)

| Script | Doel |
| ------ | ---- |
| `HermesShellCommon.Unit.Tests.ps1` | Launch UI helpers, git, repo paths |
| `HermesWebDashboardLaunch.Unit.Tests.ps1` | Web-deps manifest, pygount-cache mismatch/clear |
| `HermesUiTuiNpm.Unit.Tests.ps1` | ui-tui npm workspace, vitest-ready paths, edge cases (temp dirs) |

```powershell
powershell -NoProfile -File windows\tests\HermesWebDashboardLaunch.Unit.Tests.ps1
powershell -NoProfile -File windows\tests\HermesUiTuiNpm.Unit.Tests.ps1
```

## `RUN_PYTEST` (shim → fork gate)

Zie **[`PYTEST_POLICY.md`](PYTEST_POLICY.md)** voor gate vs upstream vs productie-poort.

- **`RUN_PYTEST_FORK_GATE.bat`** — harde poort (manifest); ~3–5 min
- **`RUN_PYTEST_UPSTREAM.bat -ReportOnly`** — volledige `tests/`, exit 0 altijd; rapport `pytest_upstream_summary.json`
- **`RUN_PYTEST.ps1`** — default fork gate; `-Upstream` voor volledige suite

### Gedrag fork gate

- Zet de werkmap op de **repo-root** (`hermes-agent`).
- Gebruikt **`Get-HermesAuditPython`** / conda `hermes-env`.
- Zet test-API-keys leeg (zoals CI).
- Draait **`pytest -n 0`** (serieel) via **`Invoke-HermesAuditPytest`** (`--timeout-method=thread`, 30s).
- Paden/markers uit **`pytest_fork_gate.yaml`** (geen hardcoded overlay/profile subset).
- **`Get-HermesPytestArgsFromConfig`** bouwt argv; upstream `--maxfail` / `--junitxml` blijven **gescheiden** (PS 5.1 `@()`-valkuil).
- **`Invoke-HermesAuditPytest`** negeert pytest teardown-warnings op stderr (`ErrorAction Continue`).
- Runners lezen **`$global:LASTEXITCODE`** na `Tee-Object` (pipeline clobber-fix).
- Log: **`RUN_PYTEST_fork_gate.log`** (gitignored).

### Gebruik

```text
Dubbelklik: RUN_PYTEST_FORK_GATE.bat
```

Productie-poort (TUI + gate + AllE2E):

```text
windows\audits\RUN_PRODUCTION_GATE.bat
```

Of vanuit PowerShell:

```powershell
cd d:\pad\naar\hermes-agent
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\tests\RUN_PYTEST_FORK_GATE.ps1
```

Extra pytest-argumenten (upstream only via `-Upstream`):

```powershell
.\windows\tests\RUN_PYTEST.ps1 -Upstream tests\tools\test_search_hidden_dirs.py -q
```

## `Test-PsesTokenizer.ps1`, `HermesShellCommon` en `MemoryAuditCommon` unit tests

- **`Test-PsesTokenizer.ps1`**: AST-parse (zelfde tokenizer als PSES) voor fork-kritieke `windows\*.ps1` scripts (incl. identity repair).
- **`HermesShellCommon.Unit.Tests.ps1`**: `Format-HermesStepLabel`, `Test-NativeCommandFailed`, `Join-HermesRepoPath` (geen Pester).
- **`MemoryAuditCommon.Unit.Tests.ps1`**: identity allowlist, `Repair-HermesIdentityLine`, runtime/repo scrub, skip zonder `config.yaml`.
- **`TrustRuntimePending.Unit.Tests.ps1`**: stamp, attempts, max-pogingen, corrupte/leeg JSON (geïsoleerde `LOCALAPPDATA`).
- **`TrustRuntimeSync.Unit.Tests.ps1`**: trust-runtime stamp/drift, watch-paden, profile-completeness, memory-audit gate, `Test-TrustRuntimeSyncNeeded` (geïsoleerde `LOCALAPPDATA` + mini-repo).
- **`HermesSessionMaintenance.Unit.Tests.ps1`**: stamps, domains fingerprint, model `-AllowFailure`, start/post-pull mocks (geïsoleerde `LOCALAPPDATA`, geen live RAG-ingest).
- **`LegalDomainE2E.Unit.Tests.ps1`**: `LegalDomainE2E.core.ps1` met geïsoleerde `HermesRoot`/`UserDataRoot`, `-StrictSources`, bronmap FAIL/PASS (pytest/rooktest uit via env).
- **`Invoke-MemoryTrustPostSync.Unit.Tests.ps1`**: mock runtime, notice JSON, skip scrub (geen production gate).
- **`tests\windows\test_memory_identity_repair.ps1`**: geïsoleerde runtime mock (legacy runner).
- **`tests\windows\test_scrub_identity.py`**: pytest parity met PS1 allowlist.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\tests\Test-PsesTokenizer.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\tests\HermesShellCommon.Unit.Tests.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\tests\MemoryAuditCommon.Unit.Tests.ps1
```

E2E-poorten: **`RUN_HERMES_SHELL_COMMON_E2E.bat`**, **`RUN_MEMORY_IDENTITY_REPAIR_E2E.bat`**, **`RUN_MEMORY_TRUST_INTEGRATION_E2E.bat`** (10/10 — alleen deze audit via `RUN_*.bat`).

**Sessie-onderhoud:** `pytest tests\windows\test_hermes_session_maintenance.py tests\audits\test_session_maintenance_e2e_harness.py -q -m "not e2e"` · volledige keten: `audits\RUN_SESSION_MAINTENANCE_E2E.bat` (14/14).

**IDE parent workspace:** vóór vertrouwen op de Problems-lijst: **`APPLY_WORKSPACE_IDE_SETTINGS.bat`** + Reload Window — `docs/WORKSPACE_IDE_SETUP.md`.

## `RUN_PSScriptAnalyzer`

- Vereist dat **PSScriptAnalyzer** al op de machine staat (`Get-Module -ListAvailable PSScriptAnalyzer`). Er is **geen** automatische `Install-Module` (die hangt vaak vast in IDE/headless); eenmalig in een gewone PowerShell:

  `Install-Module -Name PSScriptAnalyzer -Scope CurrentUser -Repository PSGallery -Force -AllowClobber`

- **Exitcode 1** bij ten minste één **Error**-severity (warnings blokkeren niet; zie **`windows\PSScriptAnalyzerSettings.psd1`**). Ontbrekende module → ook exit **1** met dezelfde install-regel.

```text
Dubbelklik: RUN_PSScriptAnalyzer.bat
```

```powershell
.\windows\tests\RUN_PSScriptAnalyzer.ps1
```

### Om een volledige pytest-run echt tot 100% te laten komen

1. **Installeer dev-deps** (bevat `pytest-timeout`): vanuit repo-root `pip install -e ".[dev]"` in `hermes-env`, of minstens `pip install pytest-timeout`.
2. **Taakplanner / Cursor / CI**: zet *geen* agressieve **“stop na X minuten”** op het pytest-proces tenzij X ruim boven de verwachte suitesduur ligt (duizenden tests). Een halve run + **4294967295 (-1)** wijst meestal op **extern beëindigen**, niet op pytest-fouten.
3. **`PYTEST_TIMEOUT`** (pytest-timeout): optioneel per sessie. Fork gate/upstream gebruiken **`Invoke-HermesAuditPytest`** (standaard **30s**, `--timeout-method=thread`).
4. Bij een timeout-failure: open **`windows\tests\RUN_PYTEST_fork_gate.log`** (gate) of **`RUN_PYTEST_upstream.log`** (upstream).

## Gateway login-autostart (Windows)

| Script | Doel |
|--------|------|
| `windows\GATEWAY_INSTALL_LOGIN.bat` | Eerste install: Scheduled Task + UAC (autostart bij login) |
| `windows\GATEWAY_ENSURE_RUNNING.bat` | Geen UAC: `.cmd` vernieuwen + task/start + status |
| `windows\GATEWAY_STATUS.bat` | Alleen `hermes gateway status` |

E2E-wiring fork gate (manifest + loaders, geen volledige suite): `audits\RUN_PYTEST_FORK_GATE_E2E.bat` (11/11).

E2E-wiring gateway (geen live UAC): `audits\RUN_GATEWAY_WINDOWS_INSTALL_E2E.bat` (6 stappen).

`Last Run Result: 1` bij Scheduled Task is op Windows vaak normaal: `pythonw` start op de achtergrond en de wrapper `.cmd` eindigt direct.

## Verwachting

CI draait op **Linux**. Op Windows kunnen er nog steeds **falende tests** zijn (paden, shell, signalen). Gebruik deze runners om **lokaal** te itereren; definitieve groen = **GitHub Actions** of WSL2.

## Stoppen

Lang lopende pytest: sluit het venster of **Ctrl+C**. Eventuele achtergrond-workers: Taakbeheer → `python.exe` met `pytest` in de opdrachtregel beëindigen.

## Afsluitcodes (Windows)

- **4294967295** (unsigned weergave van **-1**): het pytest-proces is **niet netjes beëindigd** — meestal handmatig gestopt (venster sluiten, Ctrl+C, Taakbeheer, timeout of systeem). Geen betrouwbare pytest-failurecode; start `RUN_PYTEST` opnieuw voor een volledige seriële run.
- **3**: pytest **INTERNALERROR** (o.a. xdist-worker crash op Windows bij `-n auto` / worker teardown). Gebruik **`pytest -n 0`** via deze runner in plaats van parallel.

Algemene **audit**-keten (PSScriptAnalyzer, ruff, footguns, npm, geen pytest): **`windows\audits\README.md`** (*Afsluitcodes* / stoppen).
