# Institutionele operaties — Hermes Windows-fork

Runbook voor dagelijks gebruik, recovery en release-validatie.

## Handige commando's (fork)

**Canonical cheat sheet** — alle paden vanuit repo-root `hermes-agent\`. Uitgebreide tabellen per domein: [`windows/README.md`](../windows/README.md), documentatie-index [`docs/README.md`](README.md).

### Dagelijks & na `git pull`

```cmd
start_hermes.bat
start_hermes.bat --pull
start_hermes.bat --pull -Full
start_hermes.bat --sync
start_hermes.bat --no-pull
set HERMES_SKIP_AUTO_PULL_ON_START=1
windows\POST_GIT_PULL.bat -SkipRelaunch
windows\POST_GIT_PULL.bat -QuickFix
windows\SYNC_TRUST_RUNTIME.bat
```

**Eén entrypoint:** `start_hermes.bat` — detecteert automatisch of pull nodig is (`Test-HermesGitPullNeeded.ps1`); zo niet, direct chat. `--pull` forceert; `--no-pull` slaat auto-pull over.

**Launch-profiel (Windows):** standaard **full** via `start_hermes.bat` (SOUL, institutioneel, trust, Docker, dashboard). Snel alleen chat: `start_hermes_minimal.bat`. Canoniek: [`windows/launch_profiles.ps1`](../windows/launch_profiles.ps1), [`windows/START.md`](../windows/START.md). Voorkeur opslaan: `windows\set_launch_profile.bat full|minimal`.

`start_hermes.bat` → `launch_hermes.ps1` → orchestrator start dashboard bij profiel **full** (Codebase Viz warmup): **`hermes dashboard --no-open`** op `http://127.0.0.1:9119` (geen browser-tab; open zelf `/sessions`). Uitzetten: `HERMES_SKIP_DASHBOARD_ON_START=1` of `HERMES_DASHBOARD_ON_START=0`. Log: `output\research\logs\hermes_dashboard.log`.
Windows Terminal is verplicht (`windows/requirements-windows.txt`; `INSTALL_WINDOWS_TERMINAL.bat`). `start_hermes.bat` zet `HERMES_AUTO_WINDOWS_TERMINAL=1` (start in `wt -M` wanneer `wt.exe` beschikbaar). Uitzetten: `HERMES_SKIP_WINDOWS_TERMINAL=1`. Console-layout: `HERMES_CONSOLE_LAYOUT=maximized` — in **WT geen** conhost work-area expand (titelbalk veilig); legacy cmd wel werkgebied. Zie [`windows/MOUSE_OVERLAY_FIX.md`](../windows/MOUSE_OVERLAY_FIX.md). Bij titelbalk-muis vast na pull: `windows\FIX_MOUSE_BLOCKED.bat` → alle tabs dicht → `start_hermes.bat`.

**Na pull (standaard):** `start_hermes.bat --pull` of `start_hermes.bat --pull -Full` — sync (trust, SOUL, drift, display) + **Hermes-relaunch** in Windows Terminal. Alleen sync: `--sync` of `windows\POST_GIT_PULL.bat`. Uitzetten relaunch: `-SkipRelaunch` op dezelfde regel; daarna start `start_hermes.bat` zelf de chat op. `PULL_HERMES.bat` blijft werken (doorverwijzing).

`-QuickFix` ruimt ongetrackte root-rommel op **vóór** verify. Optioneel: `-IncludeCodebaseSmoke`, `-IncludeCodebaseSmokeE2E`, `-IncludeRagPipeline` (lang), `windows\RAG_PIPELINE.bat`.

**Validatie (zonder live Hermes-kill):**

```cmd
audits\RUN_POST_GIT_PULL_AUTOMATION_E2E.bat
pytest tests\audits\test_post_git_pull_automation_e2e_harness.py -q -m "not e2e"
pytest tests\windows\test_post_git_pull_args.py tests\windows\test_stop_hermes_cli_processes.py tests\hermes_cli\test_cli_post_sync_new_chat.py -q
```

Relaunch-keten: `windows\scripts\Invoke-HermesPostPullRelaunch.ps1` (gateway stop, `stop_other_hermes_processes.ps1`, `pip install -e .`, `.update_check` wissen, `repair_gateway_home`, WT via `Invoke-HermesLaunchInWindowsTerminal`). Trust bij FAIL: `Invoke-PostGitPullTrustOutcome.ps1` → `pending_trust_runtime.json`. Klassieke CLI: `_apply_post_sync_new_chat_notice` na `_init_agent` (lege history = ack; anders `new_session(silent=True)`).

### Codebase Viz (dashboard-plugin)

Bundled tab **Codebase Viz** op `/codebase-viz` (na Skills). Bij workspace-start zet `windows\scripts\launch_dashboard_on_start.ps1`:

| Env | Default (fork) | Doel |
|-----|----------------|------|
| `HERMES_BUNDLED_PLUGINS` | `<repo>\plugins` | Workspace `plugin_api.py` v2.5.0 (geen oude user-kopie) |
| `CODEBASE_VIZ_PYGOUNT_TIMEOUT` | `240` | pygount subprocess-timeout (volledige repo) |
| `CODEBASE_VIZ_REPO` | hermes-agent root | Optioneel: ander scan-doel |
| `CODEBASE_VIZ_SCAN_MODE` | `incremental` | Productie: stale-while-revalidate + delta-refresh; `full` voor expliciete full rebuilds |
| `HERMES_CODEBASE_VIZ_WARMUP` | `auto` | Na health: POST `/force-scan` (achtergrond); `incremental` = alleen health; `0` = uit |
| `HERMES_CODEBASE_VIZ_SKIP_BUILD` | *(uit)* | Geen `npm run build` als `src/` nieuwer is dan `dist/index.js` |

Bij Hermes-start (standaard): pip `[web]` + pygount, optioneel `npm run build`, dashboard op 9119, health-verify, daarna force-scan warmup.

**Na start controleren:**

```cmd
audits\verify_codebase_viz_health.py
```

Verwacht: `version=2.5.0`, `pygount_timeout_sec=240`, `plugin_api_path` onder deze repo.

Bij `scan_mode=incremental` serveert de plugin direct gecachte payloads (`/structure`, `/summary`, `/dependencies`) en start daarna background refresh met delta-detectie. UI/WS tonen refresh-events (`refresh_started`, `delta_detected`, `refresh_done`).

**Alles-in-één na codewijziging (aanbevolen):**

```cmd
hermes_onderhoud.bat
```

Alleen dashboard: `hermes_onderhoud.bat -DashboardOnly` (alias: `audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat`).

**Incidenten:**

| Symptoom | Actie |
|----------|--------|
| Fout met **30 seconds** | Oud dashboard-proces; `RESTART_CODEBASE_VIZ_DASHBOARD.bat` of Hermes volledig afsluiten |
| **timeout na 240s** | `set CODEBASE_VIZ_PYGOUNT_TIMEOUT=300` vóór start, of tijdelijk kleinere `CODEBASE_VIZ_REPO` |
| **pygount failed** | `conda run -n hermes-env python -m pip install pygount` (launch-script installeert dit bij workspace-plugins) |
| Geen live file-watcher | Normaal op Windows native; WSL alleen als WS-updates productiekritisch zijn |
| **`memory_pressure` in Sunburst** | `windows\FIX_CODEBASE_VIZ_CACHE.bat`, dashboard herstarten; zie [`docs/CODEBASE_VIZ_TROUBLESHOOTING.md`](CODEBASE_VIZ_TROUBLESHOOTING.md) |
| **`401` op `/api/.../health` in browser** | API vereist `X-Hermes-Session-Token` (console-fetch op `/codebase-viz` of verify-script) |

Rooktest-checklist: [`docs/checklists/codebase-viz-sprint4-full-gate.md`](checklists/codebase-viz-sprint4-full-gate.md). Plugin-README: [`plugins/codebase-viz/dashboard/README.md`](../plugins/codebase-viz/dashboard/README.md).

### Repo-hygiene & snelle poorten

```cmd
windows\UPDATE_HERMES.bat -QuickFix
windows\scripts\health_check_repo.ps1
powershell -NoProfile -File windows\scripts\guard_git_clean.ps1 -Strict

windows\audits\RUN_AUDITS.bat -IncludeInstitutionalHardeningE2E
audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat

pip install pre-commit
pre-commit install
```

| Commando | Duur / scope |
|----------|----------------|
| `-IncludeInstitutionalHardeningE2E` | ~20s — QuickFix + legal pytest + preflight-log (**14/14**) |
| `-IncludeRepoHygieneE2E` | ~10s — guard, gitignore, skills + fork keys legal/creative (**9/9**) |
| `-IncludeUpdateHermesIntegrationE2E` | ~7s — UPDATE/QuickFix wiring (**12/12**) |
| `audits\RUN_CREATIVE_DOMAIN_E2E.bat` | ~10s — creative domein manifest/docs/SOUL/provision (**11/11**) |
| `audits\RUN_DASHBOARD_ON_START_E2E.bat` | ~15s — dashboard bij launch (`--no-open`, wiring + unit tests) (**7/7**) |
| `windows\audits\RUN_WT_MOUSE_OVERLAY_E2E.bat` | ~5s pytest + **handmatige** WT-titelbalk-checklist (overlay/muis; zie MOUSE_OVERLAY_FIX) |
| `audits\RUN_LEGAL_SKILLS_ROOKTEST.bat` | Snelle legal-skills pytest |
| `pytest tests\audits\test_creative_domain_e2e_harness.py -q` | Unit + mocks voor creative E2E-harness |
| `pytest tests\windows\test_repo_hygiene_institutional_e2e.py -m e2e -q` | Zelfde E2E via pytest (Windows) |
| `audits\RUN_INSTITUTIONAL_PIPELINE_E2E.bat` | ~12s — single-normalize, compact check, streaming, score verify (**11/11**) |
| `pytest tests\audits\test_institutional_pipeline_e2e_harness.py -q` | Unit + mocks voor pipeline E2E-harness (`-m e2e` = volledige harness) |
| `pytest tests\hermes_cli\test_render_pipeline_contract.py -q` | Productie-contract: 1× normalize, finalize-only stream |
| `python scripts\score_institutional_render.py --verify` | Rooktest-score ≥ 9.0/10 |
| `python scripts\bench_normalize_markdown.py` | Lokale normalizer-benchmark (geen CI-gate) |

Guard-log (lokaal): `windows\_upstream_sync_guard.log`. CI op push: `.github/workflows/fork-windows-institutional.yml`.

### Upstream (Nous → fork)

```cmd
windows\SYNC_NOUS.bat
windows\UPDATE_HERMES.bat
windows\UPDATE_HERMES_YES.bat
windows\hermes_update.bat
windows\POST_GIT_PULL.bat
windows\MERGE_UPSTREAM.bat -PromptOnly
powershell -NoProfile -File windows\upstream_sync.ps1 -Phase Preflight
```

Grote achterstand zonder j/N-vraag: `UPDATE_HERMES.bat -Yes` of `UPDATE_HERMES_YES.bat`. Automation: `set HERMES_SKIP_PAUSE_AFTER_UPDATE=1`. Alleen `-QuickFix` als enig argument: stopt na opruimen. Zie [`windows/UPSTREAM_SYNC.md`](../windows/UPSTREAM_SYNC.md).

**Tier A drift (cadans):**

| Wanneer | Commando |
|---------|----------|
| Wekelijks / vóór release | `windows\SYNC_NOUS.bat -Yes` → `powershell -File windows\scripts\Test-NousTreeIdentical.ps1` |
| Na sync/merge | `powershell -File windows\scripts\Export-NousDriftBaseline.ps1` |
| Bij update (optioneel hard stop) | `windows\UPDATE_HERMES.bat -StrictNousSync` — breekt af bij Tier-A-drift |
| Herstel Tier A | `powershell -File windows\scripts\Invoke-RestoreNousTierA.ps1` |

Zie [`docs/NOUS_OVERLAY_ARCHITECTURE.md`](NOUS_OVERLAY_ARCHITECTURE.md) en [`docs/NOUS_DRIFT_BASELINE.md`](NOUS_DRIFT_BASELINE.md).

### Release & zware poorten

```cmd
windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat
windows\audits\RUN_AUDITS.bat -IncludeInstitutionalProductionGate
windows\audits\RUN_AUDITS.bat -IncludeAllE2E
windows\VERIFY_WINDOWS_CHAIN.bat
```

`-IncludeAllE2E` bevat hardening **14/14**, maar **niet** `RUN_INSTITUTIONAL_PRODUCTION_GATE` (gebruik `-IncludeInstitutionalProductionGate` of losse `.bat`, ~2+ min).

**Aanbevolen release-keten (fork):** `RUN_REPO_HYGIENE_E2E` → `RUN_NOUS_OVERLAY_AFWERKING_E2E` → `RUN_PYTEST_AUDIT_ENV_E2E` → `RUN_RUN_AUDITS_14_FIXES_E2E` → `RUN_INSTITUTIONAL_PRODUCTION_GATE` → `Test-NousTreeIdentical` → (optioneel) `RUN_AUDITS -IncludeInstitutionalProductionGate`.

**CI vs lokaal:** PR-job (`fork-windows-institutional.yml`) = subset (~30 min). Wekelijks (`fork-windows-audits-nightly.yml`) = volledige `RUN_AUDITS -IncludeAllE2E` (~24 min).

**Pytest audit-env (snel, ~20s):** `audits\RUN_PYTEST_AUDIT_ENV_E2E.bat` — valideert `Clear-HermesPytestAddoptsForAudit`, geen dubbele `pytest_timeout`, RAG MCP bootstrap.

Platform hardening productie-poort (sandbox/file_tools wiring): `windows\audits\RUN_PLATFORM_HARDENING_PRODUCTION_GATE.bat` (ook in CI `fork-windows-institutional.yml`).

### RAG, legal & domeinen

```cmd
windows\scripts\update_knowledge.bat legal
windows\scripts\seed_rag_minimal_fixtures.ps1
windows\scripts\institutional_p0_p1.bat --ingest-remaining
windows\SYNC_DOMAIN_TOOLSETS.bat
windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing
```

**RAG fixtures (dev/CI):** `fixtures/rag_minimal/` + `seed_rag_minimal_fixtures.ps1` — smoke-inhoud, geen gevoelige data. E2E: `audits\RUN_RAG_MINIMAL_FIXTURE_E2E.bat`. **Productie:** handmatig vullen van `%USERPROFILE%\data\raw_source_files\` met echte bronnen; lege mappen = verwachte WARN buiten fixture-mode.

**Git Tier A vs runtime:** `Test-NousTreeIdentical` = repo HEAD vs upstream. `verify_hermes_config_drift` = `%LOCALAPPDATA%\hermes` runtime (strip preflight in `RUN_AUDITS -IncludeAllE2E`).

Legal E2E: `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat` · `RUN_AUDITS.bat -IncludeLegalDomainE2E`.

### Creative — eerste setup (14e profiel)

Eenmalig na toevoegen van domein `creative` (zie [`domains.yaml.example`](domains.yaml.example) → `%USERPROFILE%\data\domains.yaml`, blueprint [`DOMAIN_BLUEPRINT.md`](DOMAIN_BLUEPRINT.md)). Detail: [`13_Creative/ONBOARDING.md`](13_Creative/ONBOARDING.md).

```cmd
set HERMES_HOME=%LOCALAPPDATA%\hermes
windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing
python scripts\rag_pipeline\sync_profile_mcp_from_domains.py --domain creative
windows\LANCEDB_MAINTENANCE.bat --init-missing
windows\scripts\update_knowledge.bat creative
windows\SYNC_SOUL_SNIPPETS.bat
```

**Hyperframes** (optional skill, motion-graphics/HTML→MP4 — niet bundled):

```cmd
hermes skills install official/creative/hyperframes
bash optional-skills/creative/hyperframes/scripts/setup.sh
npx hyperframes doctor
```

| Commando | Geautomatiseerd in `POST_GIT_PULL` / `UPDATE_HERMES`? |
|----------|--------------------------------------------------------|
| `SYNC_TRUST_RUNTIME.bat` | **Ja** (trust + memory; geen volledige SOUL-template deploy) |
| `launch_soul_anatomy_deploy` (SOUL + snippets) | **Ja** via `POST_GIT_PULL` — niet de losse `SYNC_SOUL_SNIPPETS.bat` |
| `SYNC_DOMAIN_TOOLSETS.bat` | **Ja** (alleen sync bestaande profielen; **geen** `--create-missing`) |
| `SYNC_SOUL_SNIPPETS.bat` | **Nee** — handmatig of `-Force` na template-wijziging |
| `LANCEDB_MAINTENANCE --init-missing` | **Nee** — zie ook [`IDE_MAINTENANCE.md`](IDE_MAINTENANCE.md) |
| `update_knowledge.bat creative` | **Nee** — UPDATE draait hooguit `--mcp-test` (alle domeinen) |
| Hyperframes install + `doctor` | **Nee** — optioneel, eenmalig |

Na setup: `audits\RUN_CREATIVE_DOMAIN_E2E.bat` (11/11) · drift alle profielen: `windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat`. Na SOUL/toolset-wijziging: `SYNC_DOMAIN_TOOLSETS.bat` → Hermes herstart + `/new`.

### Runtime, SOUL & presentatie

```cmd
windows\APPLY_INSTITUTIONAL_RUNTIME.bat
windows\APPLY_SOUL_ANATOMY_RUNTIME.bat
windows\SYNC_SOUL_SNIPPETS.bat
windows\DIAGNOSE_RENDERER.bat
```

Na deploy: Hermes/gateway herstart + `/new` · rooktest: [`templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md`](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md).

### Python & IDE (herstel)

```cmd
windows\REPAIR_PYTHON.bat
windows\REPAIR_MODEL_PROVIDER.bat
windows\APPLY_WORKSPACE_IDE_SETTINGS.bat
windows\DOCTOR_FIX.bat
```

Legal pytest (**101**, gemockt):

```cmd
%USERPROFILE%\miniconda3\envs\hermes-env\python.exe -m pytest tests\skills\test_rechtspraak_zoeken_skill.py tests\skills\test_uitspraak_parseren_skill.py tests\skills\test_web_research_legal_skill.py -q
```

## Drie lagen (Python → RAG-deps → index)

| Laag | Doel | Commando |
|------|------|----------|
| 1 — Interpreter | conda `hermes-env`, IDE-sync, venv-quarantaine | `windows\REPAIR_PYTHON.bat` |
| 2 — RAG-deps | `pip install -e ".[rag]"` + markitdown/MCP | `windows\scripts\install_rag_extras.ps1` (auto via bootstrap) |
| 3 — Index | LanceDB per domein | `windows\scripts\update_knowledge.bat` |

**Manifesten (fast-path, geen dubbele pip):**

| Bestand | Doel |
|---------|------|
| `%LOCALAPPDATA%\Hermes\rag-deps.json` | `rag_extras_verified` + `python_exe` — skip RAG-reinstall als pyproject ongewijzigd |
| `%LOCALAPPDATA%\hermes\launch_bootstrap.json` | Schema v1: repo + `pyproject_sha256` + `python_exe` — **snelle bootstrap** (geen nested PowerShell) |
| `%LOCALAPPDATA%\hermes\launch_bootstrap.stamp` | Legacy marker; wordt mee bijgewerkt met JSON-state |

**Bootstrap versnellen uitzetten (volledige ensure_*):** `set HERMES_SKIP_LAUNCH_BOOTSTRAP_FAST_PATH=1` of `HERMES_FORCE_LAUNCH_BOOTSTRAP_FULL=1` vóór `start_hermes.bat`.

Override conda: `HERMES_PYTHON`, `HERMES_CONDA_ROOT`, `HERMES_CONDA_ENV`.

## Eerste machine (clone)

1. `windows\SETUP_HERMES.bat` (bestanden + wizard + RAG-deps)
2. `windows\REPAIR_PYTHON.bat` (conda + IDE)
3. `windows\APPLY_WORKSPACE_IDE_SETTINGS.bat` (parent `Hermes_agent_WS\.vscode` — PSES uit; zie `docs/WORKSPACE_IDE_SETUP.md`)
4. `windows\scripts\update_knowledge.bat` (ingest)
5. Rooktest: `scripts/rag_pipeline/ACTIVATION.md` (A+B+C)
6. Gate: `windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` (incl. `audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat` 14/14)
7. Regressie (review-fixes): `windows\audits\RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat` (8/8)

## Canonical OPEN_SETUP-governance

- Canonieke setup-implementatie: `scripts\windows\OPEN_SETUP.bat`
- Wrapper-only ingangspunt: `windows\OPEN_SETUP.bat` (forwarder, geen eigen setup-logica)
- Setup-launchers (`windows\SETUP_HERMES.bat`, `windows\setup_hermes_windows.bat`) verwijzen naar de canonieke flow
- Herstelvolgorde bij setup-issues: 1) `windows\SETUP_HERMES.bat --files-only`, 2) `windows\OPEN_SETUP.bat`, 3) `start_hermes.bat` (canoniek entrypoint; intern `launch_hermes.bat`)

## Dagelijks

- Start: `start_hermes.bat` (bootstrap sync RAG-deps indien nodig)
- Geen handmatige `python` — conda via policy

## Na git pull

- **`PULL_HERMES.bat`** (repo-root): `git pull` + `POST_GIT_PULL` + relaunch
- `windows\POST_GIT_PULL.bat` (verify + trust + SOUL + institutional runtime + relaunch)
- Optioneel: `-QuickFix`, `-Full`, `-IncludeInstitutionalVerify`, `-IncludeRagPipeline`
- Bij pyproject-wijziging: relaunch doet `pip install -e .` (optioneel `-InstallRag` via upstream post-merge)

## Na upstream merge

- `windows\UPDATE_HERMES.bat` → preflight (guard + upstream) + `hermes update` + post-merge (trust, toolsets, RAG)
- Guard-log: `windows\_upstream_sync_guard.log` (laatste preflight-resultaten)

## Repo-hygiene (institutioneel)

| Situatie | Actie |
|----------|--------|
| Ongetrackte scripts/data in repo-root | `windows\UPDATE_HERMES.bat -QuickFix` of `windows\scripts\quick_fix_repo_hygiene.ps1` |
| Dagelijkse controle | `powershell -File windows\scripts\health_check_repo.ps1` |
| Strikte poort (CI) | `health_check_repo.ps1 -Strict` of `$env:HERMES_REPO_GUARD_STRICT=1` vóór update |
| Herbruikbare tooling | Migreer naar `skills/<categorie>/<naam>/` (AGENTS.md) |
| Alleen onderzoek | `output/research/{scripts,data,reports}/` — zie `docs/WORKSPACE_CONVENTIONS.md` |

**Skill-levenscyclus:** ad-hoc script in `output/research/scripts/` → skill in `skills/` + pytest in `tests/skills/` → vermelding in `docs/domain_toolsets.yaml` → `SYNC_DOMAIN_TOOLSETS.bat`.

**Upstream-cyclus (aanbevolen):** wekelijks `UPDATE_HERMES.bat` → controleer guard-log → na merge `POST_GIT_PULL.bat` of rooktest institutional → `/new` in actief profiel.

## Troubleshooting

| Symptoom | Actie |
|---------|--------|
| `(venv)` in prompt | `REPAIR_PYTHON.bat` — niet `hermes-env` |
| `import lancedb` faalt | `install_rag_extras.ps1` |
| IDE verkeerde interpreter | `REPAIR_PYTHON.bat` of `sync_hermes_ide_python.ps1` |
| Rode PSES-fouten in `.ps1` (runtime OK) | `APPLY_WORKSPACE_IDE_SETTINGS.bat` + Reload Window + Restart Session — `docs/WORKSPACE_IDE_SETUP.md` |
| Dubbele RAG-install | Verwijder `%LOCALAPPDATA%\Hermes\rag-deps.json` en `%LOCALAPPDATA%\hermes\launch_bootstrap.json` (of wacht op pyproject-wijziging) |
| Bootstrap stap 2 traag | Fast-path actief? Controleer `launch_bootstrap.json` + `rag-deps.json`; geforceerd volledig: `HERMES_SKIP_LAUNCH_BOOTSTRAP_FAST_PATH=1` |
| RAG-sync mislukt bij start | Bootstrap-state niet bijgewerkt — retry bij volgende start; log in bootstrap |
| REPAIR hangt op Read-Host | Gebruik `-NonInteractive` of `HERMES_NONINTERACTIVE=1` (automatisch in CI/audit) |
| UPDATE stopt op dirty repo (exit 2) | `UPDATE_HERMES.bat -QuickFix` of commit/stash; alleen iconen: branding-waarschuwing OK |
| Rommel in repo-root | `docs/WORKSPACE_CONVENTIONS.md`, `guard_git_clean.ps1`, E2E `audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat` (14/14); gecombineerd in `RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` |
| Legacy `.venv` | Quarantaine via `ensure_hermes_python.ps1`; niet productie-default |
| Runtime 404: model niet gevonden | Startup-guard (`Test-HermesModelCatalogAvailability`) vs live Nous `/models` of manifest; run `hermes model` |
| Model-catalog mismatch | Guard accepteert o.a. `:free`-varianten (`stepfun/…:free`) via `model_default_passes_startup_catalog_guard`; opt-in repair: `HERMES_AUTOREPAIR_MODEL_CATALOG=1` |
| Extra dashboard-venster bij start | Standaard hidden; override via `HERMES_DASHBOARD_WINDOW_STYLE=minimized|normal` |

## Pre-release (handmatig)

1. `RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` (Python + platform + repo-hygiene hardening)
2. Optioneel los: `pytest tests/windows/test_repo_hygiene_institutional_e2e.py -m e2e`
3. `POST_GIT_PULL.bat` of dry-run UPDATE
4. ACTIVATION rooktest op legal-profiel

Zie ook: `docs/HERMES_START.md`, `windows/INSTITUTIONAL.md`.
