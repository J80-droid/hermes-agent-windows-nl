# Windows audits (optioneel)

Deze map bevat de **fork** kwaliteitspoorten (geen 1:1 upstream-kloon).

| Runner | Doel |
| ------ | ---- |
| **`RUN_AUDITS.bat`** | Gecombineerd: `verify_hermes_home`, PSScriptAnalyzer (SKIP indien ontbreekt), `check-windows-footguns.py`, ruff (SKIP), pytest profiel-subset |
| **`RUN_AUDITS.bat -IncludeProfileE2E`** | Bovenstaande + profielwissel E2E |
| **`RUN_AUDITS.bat -IncludeInstitutionalE2E`** | Bovenstaande + landkaart/SOUL-backup/templates E2E |
| **`RUN_AUDITS.bat -IncludeAllE2E`** | Institutioneel + legal-domein + profielwissel E2E |
| **`RUN_AUDITS.bat -IncludeLegalDomainE2E`** | Legal taxonomie, SOUL, submappen, rooktest |
| **`APPLY_INSTITUTIONAL_RUNTIME.bat`** | **Automatisch:** display (alle profielen) + SOUL-sync + E2E |
| **`RUN_INSTITUTIONAL_E2E.bat`** | Audit alleen (8 stappen); `-ApplyRuntime` = eerst runtime toepassen |
| **`RUN_INSTITUTIONAL_E2E.bat -ApplyRuntime`** | Zelfde als `APPLY_INSTITUTIONAL_RUNTIME.bat` (zonder dubbele E2E) |
| **`RUN_LEGAL_DOMAIN_E2E.bat`** | Legal lenzen, actieve zaken, bronlayout |
| **`RUN_AUDITS.bat -RequirePSScriptAnalyzer`** | PSSA verplicht (exit 1 als module ontbreekt) |
| **`RUN_PROFILE_SWITCH_E2E.bat`** | Alleen profielwissel E2E |
| **`windows\tests\RUN_PYTEST.bat`** | Brede pytest (excl. integration) |
| **`windows\VERIFY_WINDOWS_CHAIN.bat`** | Script-keten backup/RAG (handmatig, pause) |
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

Stappen: repo-artefacten → pytest (landkaart + **presentatie/markdown**) → landkaart CLI smoke → `backup_soul_profiles` → runtime SOUL Interaction + Outputformaat → display config + rich_output smoke → restore/update regressie.

Presentatie: zie `docs/INSTITUTIONAL_PRESENTATION.md`. **Eén commando:** `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` (of E2E met `-ApplyRuntime`). Display-check stap 6/8: **alle** profielen onder `profiles\`.

Laatste rapport: `INSTITUTIONAL_E2E_REPORT_2026-05-22.md` (log `INSTITUTIONAL_E2E_LAST_RUN.log` is gitignored).

## Profielwissel E2E

```text
Dubbelklik of: windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Stappen: HERMES_HOME-root check → unit tests → `SWITCH_PROFILE.bat legal` → smoke `HERMES_HOME=profiles\core` + `-p legal` → sticky terug naar `core`.

Sync naar `%USERPROFILE%\.hermes\_local_assets\` kopieert dit README + audit-runners mee waar geconfigureerd.

## Landkaart-skill

Na `git pull` of `UPDATE_HERMES.bat`: nieuwe sessie of `hermes update` zodat skill `landkaart` en slash `/landkaart` geladen zijn. Script: `skills/productivity/landkaart/scripts/inventory_landkaart.py` (unit tests in `tests/`).
