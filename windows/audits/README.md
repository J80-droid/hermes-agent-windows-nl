# Windows audits (optioneel)

Deze map bevat de **fork** kwaliteitspoorten (geen 1:1 upstream-kloon).

| Runner | Doel |
| ------ | ---- |
| **`RUN_AUDITS.bat`** | Gecombineerd: `verify_hermes_home`, PSScriptAnalyzer (SKIP indien ontbreekt), `check-windows-footguns.py`, ruff (SKIP), pytest profiel-subset |
| **`RUN_AUDITS.bat -IncludeProfileE2E`** | Bovenstaande + profielwissel E2E |
| **`RUN_AUDITS.bat -IncludeInstitutionalE2E`** | Bovenstaande + landkaart/SOUL-backup/templates E2E |
| **`RUN_AUDITS.bat -IncludeAllE2E`** | Institutioneel + legal-domein + profielwissel + toolset + SOUL deploy-start E2E |
| **`RUN_SOUL_DEPLOY_START_E2E.bat`** | Stamp/startketen: launch_hermes, POST_GIT_PULL, upstream SkipSoul, anatomy subset |
| **`RUN_AUDITS.bat -IncludeSoulDeployStartE2E`** | Alleen SOUL deploy-start E2E |
| **`RUN_AUDITS.bat -IncludeToolsetDomainE2E`** | `platform_toolsets.cli` per profiel vs manifest |
| **`RUN_AUDITS.bat -IncludeLegalDomainE2E`** | Legal taxonomie, SOUL, submappen, rooktest |
| **`APPLY_INSTITUTIONAL_RUNTIME.bat`** | Handmatig: display + SOUL + E2E; **automatisch** na `UPDATE_HERMES.bat` (post-merge, `-SkipE2E`) |
| **`RUN_INSTITUTIONAL_E2E.bat`** | Audit (11 stappen incl. profiel-chat-UX); `-ApplyRuntime` = eerst runtime |
| **`RUN_INSTITUTIONAL_E2E.bat -ApplyRuntime`** | Zelfde als `APPLY_INSTITUTIONAL_RUNTIME.bat` (zonder dubbele E2E) |
| **`RUN_LEGAL_DOMAIN_E2E.bat`** | Legal lenzen, actieve zaken, bronlayout |
| **`RUN_TOOLSET_DOMAIN_E2E.bat`** | 6-stappen E2E: home verify, manifest, pytest, drift, tool-counts, SOUL governance |
| **`RUN_PROVISION_DOMAIN_E2E.bat`** | Smoke: `--create-missing` op tijdelijke HERMES_HOME (geen productie) |
| **`RUN_AUDITS.bat -IncludeProvisionDomainE2E`** | Alleen provision-smoke |
| **`RUN_AUDITS.bat -RequirePSScriptAnalyzer`** | PSSA verplicht (exit 1 als module ontbreekt) |
| **`windows\tests\RUN_PSScriptAnalyzer.bat`** | Volledige `windows\` lint (instellingen: `PSScriptAnalyzerSettings.psd1`) — verwacht **0 Warning/Error** |
| **`RUN_PROFILE_SWITCH_E2E.bat`** | Alleen profielwissel E2E |
| **`windows\tests\RUN_PYTEST.bat`** | Brede pytest (excl. integration) |
| **`windows\VERIFY_WINDOWS_CHAIN.bat`** | Script-keten backup/RAG (handmatig, pause) |
| **`RUN_BACKUP_E2E.bat`** | Lightweight backup schema v3 test (`tests/windows/test_backup_runtime.ps1`) |
| **`UPDATE_HERMES.bat`** | Zelfde verify via `verify_windows_script_chain.ps1` in keten (geen pause) |

## Legal domein E2E

```text
windows\audits\RUN_LEGAL_DOMAIN_E2E.bat
```

Stappen: repo taxonomie → runtime SOUL (geen GCR in Identity) → `LEGAL_ACTIVE_MATTERS.md` → submappen `04_Legal_Corporate` → taxonomy-sync dry-run → pytest → rooktest search.

Bron-migratie: `windows\scripts\MIGRATE_LEGAL_LAYOUT.bat -Apply` daarna `update_knowledge.bat legal`.

## Institutioneel E2E (landkaart + SOUL)

```text
windows\audits\RUN_INSTITUTIONAL_E2E.bat
```

Stappen: repo → pytest (landkaart, presentatie, **2d profiel-chat-UX**, **2e Rich renderer**) → landkaart smoke → backup → SOUL Interaction/Outputformaat/**5c profielwissel-regel** → display alle profielen (incl. `assistant_render_style`, `assistant_palette`, `assistant_label_columns`) → rich_output → restore/update → **pytest profielwissel** → **SWITCH legal→core** → intent-smoke.

### Wat de institutioneel E2E **wel** dekt (sinds 11 stappen)

| Onderdeel | Stap |
| --------- | ---- |
| Natuurlijke taal → profielnaam (`cli._parse_profile_switch_intent`) | 2d, 11 |
| Prompt gebruikt sticky `active_profile` (niet verkeerd HERMES_HOME-pad) | 2d |
| SOUL Interaction: `/profile use`, geen advies “alleen buiten sessie” | 5c |
| Sticky wissel via `SWITCH_PROFILE.bat` + pytest profiel-subset | 9, 10 |

### Wat deze E2E **niet** deed (bewust of apart script)

| Gap | Waarom / waar |
| --- | ------------- |
| Gebruiker zegt in chat “schakel naar core” → **agent** antwoordt met `/profile use core` | Geen live LLM; model kan oude context hebben. Handmatig: nieuwe chat na SOUL-sync. |
| Prompt toont direct `core ❯` **na** natuurlijke taal in dezelfde lopende sessie | 2d test code/prompt-logica, geen terminal-herstart na intent-intercept. |
| Volledige profielwissel-E2E (alle varianten) | `windows\audits\RUN_PROFILE_SWITCH_E2E.bat` (`SWITCH_PROFILE.bat`, `test_profile_switch_e2e`, …). |
| SOUL Interaction-regels **in gedrag** na lange sessie | 5c leest alleen tekst op schijf; geen sessie met verouderde SOUL in context. |

**Handmatig na deploy:** `APPLY_INSTITUTIONAL_RUNTIME.bat` → Hermes herstarten → **nieuwe chat** → profielwissel via `/profile use <naam>` of natuurlijke zin (CLI voert wissel uit vóór het model).

Presentatie: zie `docs/INSTITUTIONAL_PRESENTATION.md`. **Eén commando:** `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` (of E2E met `-ApplyRuntime`). Display-check stap 6/11: **alle** profielen onder `profiles\`.

Laatste rapport: `INSTITUTIONAL_E2E_REPORT_2026-05-22.md` (log `INSTITUTIONAL_E2E_LAST_RUN.log` is gitignored).  
Upstream + UPDATE audit: `UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md`.

## Domein-toolsets E2E

```text
windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat
```

Of via gecombineerde poort:

```text
windows\audits\RUN_AUDITS.bat -IncludeToolsetDomainE2E
```

| Stap | Controle |
| ---- | -------- |
| 1/6 | `verify_hermes_home` (+ auth.json repair indien corrupt) |
| 2/6 | Repo: `domain_toolsets.yaml`, audit-doc, sync-scripts |
| 3/6 | pytest: manifest + lege `cli: []` (geen hermes-cli/MCP/kanban-lek) |
| 4/6 | Runtime drift: `sync_profile_toolsets_from_manifest.py --check` |
| 5/6 | Per profiel: `platform_toolsets.cli`, tool-count ≤ `max_tools`, root = **0 tools** |
| 6/6 | SOUL: Tool governance in `core` + `legal` |

**Vóór audit (bij drift):** `windows\SYNC_DOMAIN_TOOLSETS.bat`

**Schone machine / ontbrekend profiel in manifest:** eerst `windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing` (zet `HERMES_HOME` op root, niet `profiles\legal`). Smoke: `RUN_PROVISION_DOMAIN_E2E.bat`.

**Rapport:** `TOOLSET_DOMAIN_E2E_LAST_RUN.log` (gitignored)

**Handmatig na PASS:** nieuwe chat met `hermes -p <domein>` — root zonder `-p` heeft bewust geen tools.

Zie `docs/DOMAIN_TOOLSET_AUDIT.md`.

## SOUL deploy bij start E2E

```text
windows\audits\RUN_SOUL_DEPLOY_START_E2E.bat
```

| Stap | Controle |
| ---- | -------- |
| 1/8 | Repo-keten: `launch_soul_anatomy_deploy`, `launch_hermes` volgorde, `POST_GIT_PULL -Force`, geen `SOUL_ANALYST_DOMAIN` |
| 2/8 | `Get-SoulAnatomyWatchPaths`, 13 profielen |
| 3/8 | Stamp-logica (isolated temp; geen repo-touch) |
| 4/8 | `HERMES_SKIP_SOUL_DEPLOY_ON_START=1` |
| 5/8 | Productie-stamp → `up-to-date` (skip indien geen stamp) |
| 6/8 | `launch_institutional_runtime` zonder SOUL-watch, met `SkipSoul` na deploy |
| 7/8 | `sync_all` exit-codes + `-UpdateDeployStamp` |
| 8/8 | `RUN_SOUL_ANATOMY_E2E` (runtime anatomy) |

**Rapport:** `SOUL_DEPLOY_START_E2E_LAST_RUN.log` (gitignored indien in .gitignore)

**Handmatig na FAIL stap 5:** `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat`

## Profielwissel E2E

```text
Dubbelklik of: windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Stappen: HERMES_HOME-root check → unit tests → `SWITCH_PROFILE.bat legal` → smoke `HERMES_HOME=profiles\core` + `-p legal` → sticky terug naar `core`.

Sync naar `%USERPROFILE%\.hermes\_local_assets\` kopieert dit README + audit-runners mee waar geconfigureerd.

## Landkaart-skill

Na `git pull` of `UPDATE_HERMES.bat`: nieuwe sessie of `hermes update` zodat skill `landkaart` en slash `/landkaart` geladen zijn. Script: `skills/productivity/landkaart/scripts/inventory_landkaart.py` (unit tests in `tests/`).
