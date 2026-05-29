# Lokale pytest-runners (Windows)

Deze map is **niet** de upstream pytest-collectie. De echte tests staan in de repo-root: **`hermes-agent\tests\`**.

## Keuze: pytest en PSScriptAnalyzer gescheiden

**PSScriptAnalyzer** hoort **niet** standaard vóór elke pytest-run: pytest is al zwaar (duizenden tests), en PS-lint is een **andere concern** (alle `windows\*.ps1`). Je wilt tijdens Python-werk **snel** kunnen herhalen zonder module-installatie / analyse-overhead.

- **Volledige kwaliteitspoort** (PSSA + ruff + footguns + npm + ty): **`windows\audits\RUN_AUDITS.ps1`** — PSSA alleen als de module **al** geïnstalleerd is; anders **SKIP** (geen hang op PSGallery). Streng: **`RUN_AUDITS.ps1 -RequirePSScriptAnalyzer`**.
- **Alleen PowerShell onder `windows\`**: **`RUN_PSScriptAnalyzer.ps1`** (zelfde helper als audits)
- **Alleen Python-tests**: **`RUN_PYTEST.ps1`**

## Profielwissel (subset)

Snelle regressie zonder volledige suite:

```powershell
.\windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Of alleen pytest:

```powershell
python -m pytest tests/hermes_cli/test_apply_profile_override.py tests/hermes_cli/test_profile_switch.py tests/hermes_cli/test_relaunch.py::TestRelaunchChatAfterProfileSwitch -q
```

## PowerShell unit tests (launch / dashboard)

| Script | Doel |
| ------ | ---- |
| `HermesShellCommon.Unit.Tests.ps1` | Launch UI helpers, git, repo paths |
| `HermesWebDashboardLaunch.Unit.Tests.ps1` | Web-deps manifest, pygount-cache mismatch/clear |

```powershell
powershell -NoProfile -File windows\tests\HermesWebDashboardLaunch.Unit.Tests.ps1
```

## `RUN_PYTEST`

- Zet de werkmap op de **repo-root** (`hermes-agent`).
- Gebruikt **`miniconda3\envs\hermes-env\python.exe`** (pas aan als nodig).
- Zet test-API-keys leeg (zoals CI).
- Draait **`pytest -n 0`** (serieel) — op Windows voorkomt dit xdist/PosixPath-internal errors.
- Sluit **integration** en **e2e** uit; markeer **`not integration`** (zoals `pyproject`).
- Voegt **`pytest-timeout`** toe (als geïnstalleerd in die Python): op Linux beperkt `tests/conftest.py` hangende tests met **SIGALRM (~30s)**; op Windows bestaat dat niet — zonder timeout kan de run uren blijven hangen tot een taak of gebruiker het proces afbreekt (**EXIT -1**). Standaard: **60s per test** via `--timeout`, tenzij je zelf **`PYTEST_TIMEOUT`** zet (officiële variabele van pytest-timeout; dan wordt geen `--timeout` geïnjecteerd).
- Schrijft **`last_pytest_run.log`** in deze map (naast `RUN_PYTEST.ps1`) en zet **`PYTHONUNBUFFERED=1`** zodat voortgang direct zichtbaar is (handig bij Taakplanner).

### Gebruik pytest

```text
Dubbelklik: RUN_PYTEST.bat
```

Of vanuit PowerShell:

```powershell
cd d:\pad\naar\hermes-agent
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\tests\RUN_PYTEST.ps1
```

Extra pytest-argumenten worden doorgegeven (bijv. een enkele test):

```powershell
.\windows\tests\RUN_PYTEST.ps1 tests\tools\test_search_hidden_dirs.py -q
```

## `Test-PsesTokenizer.ps1`, `HermesShellCommon` en `MemoryAuditCommon` unit tests

- **`Test-PsesTokenizer.ps1`**: AST-parse (zelfde tokenizer als PSES) voor fork-kritieke `windows\*.ps1` scripts (incl. identity repair).
- **`HermesShellCommon.Unit.Tests.ps1`**: `Format-HermesStepLabel`, `Test-NativeCommandFailed`, `Join-HermesRepoPath` (geen Pester).
- **`MemoryAuditCommon.Unit.Tests.ps1`**: identity allowlist, `Repair-HermesIdentityLine`, runtime/repo scrub, skip zonder `config.yaml`.
- **`TrustRuntimePending.Unit.Tests.ps1`**: stamp, attempts, max-pogingen, corrupte/leeg JSON (geïsoleerde `LOCALAPPDATA`).
- **`TrustRuntimeSync.Unit.Tests.ps1`**: trust-runtime stamp/drift, watch-paden, profile-completeness, memory-audit gate, `Test-TrustRuntimeSyncNeeded` (geïsoleerde `LOCALAPPDATA` + mini-repo).
- **`HermesSessionMaintenance.Unit.Tests.ps1`**: stamps, domains fingerprint, model `-AllowFailure`, start/post-pull mocks (geïsoleerde `LOCALAPPDATA`, geen live RAG-ingest).
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
3. **`PYTEST_TIMEOUT`** (pytest-timeout): seconden per test voor de hele sessie. Niet gezet → deze runner gebruikt **60**. Zet bijv. **`120`** op een trage machine, of **`0`** om timeouts uit te zetten (alleen voor debug). Zie [pytest-timeout](https://github.com/pytest-dev/pytest-timeout).
4. Bij een timeout-failure: open **`windows\tests\last_pytest_run.log`** — de laatste regels tonen welke test vastliep.

## Verwachting

CI draait op **Linux**. Op Windows kunnen er nog steeds **falende tests** zijn (paden, shell, signalen). Gebruik deze runners om **lokaal** te itereren; definitieve groen = **GitHub Actions** of WSL2.

## Stoppen

Lang lopende pytest: sluit het venster of **Ctrl+C**. Eventuele achtergrond-workers: Taakbeheer → `python.exe` met `pytest` in de opdrachtregel beëindigen.

## Afsluitcodes (Windows)

- **4294967295** (unsigned weergave van **-1**): het pytest-proces is **niet netjes beëindigd** — meestal handmatig gestopt (venster sluiten, Ctrl+C, Taakbeheer, timeout of systeem). Geen betrouwbare pytest-failurecode; start `RUN_PYTEST` opnieuw voor een volledige seriële run.
- **3**: pytest **INTERNALERROR** (o.a. xdist-worker crash op Windows bij `-n auto` / worker teardown). Gebruik **`pytest -n 0`** via deze runner in plaats van parallel.

Algemene **audit**-keten (PSScriptAnalyzer, ruff, footguns, npm, geen pytest): **`windows\audits\README.md`** (*Afsluitcodes* / stoppen).
