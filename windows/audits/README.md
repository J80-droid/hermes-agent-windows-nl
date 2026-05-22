# Windows audits (optioneel)

Deze map bevat de **fork** kwaliteitspoorten (geen 1:1 upstream-kloon).

| Runner | Doel |
| ------ | ---- |
| **`RUN_AUDITS.bat`** | Gecombineerd: `verify_hermes_home`, PSScriptAnalyzer (SKIP indien ontbreekt), `check-windows-footguns.py`, ruff (SKIP), pytest profiel-subset |
| **`RUN_AUDITS.bat -IncludeProfileE2E`** | Bovenstaande + profielwissel E2E |
| **`RUN_AUDITS.bat -IncludeInstitutionalE2E`** | Bovenstaande + landkaart/SOUL-backup/templates E2E |
| **`RUN_AUDITS.bat -IncludeAllE2E`** | Beide E2E-audits |
| **`RUN_INSTITUTIONAL_E2E.bat`** | Alleen institutioneel pakket (6 stappen) |
| **`RUN_AUDITS.bat -RequirePSScriptAnalyzer`** | PSSA verplicht (exit 1 als module ontbreekt) |
| **`RUN_PROFILE_SWITCH_E2E.bat`** | Alleen profielwissel E2E |
| **`windows\tests\RUN_PYTEST.bat`** | Brede pytest (excl. integration) |
| **`windows\VERIFY_WINDOWS_CHAIN.bat`** | Script-keten backup/RAG (handmatig, pause) |
| **`UPDATE_HERMES.bat`** | Zelfde verify via `verify_windows_script_chain.ps1` in keten (geen pause) |

## Institutioneel E2E (landkaart + SOUL)

```text
windows\audits\RUN_INSTITUTIONAL_E2E.bat
```

Stappen: repo-artefacten → pytest landkaart/orchestrator → landkaart CLI smoke → `backup_soul_profiles` naar `%TEMP%` → core SOUL Interaction-check → restore/update regressie.

## Profielwissel E2E

```text
Dubbelklik of: windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Stappen: HERMES_HOME-root check → unit tests → `SWITCH_PROFILE.bat legal` → smoke `HERMES_HOME=profiles\core` + `-p legal` → sticky terug naar `core`.

Sync naar `%USERPROFILE%\.hermes\_local_assets\` kopieert dit README + audit-runners mee waar geconfigureerd.

## Landkaart-skill

Na `git pull` of `UPDATE_HERMES.bat`: nieuwe sessie of `hermes update` zodat skill `landkaart` en slash `/landkaart` geladen zijn. Script: `skills/productivity/landkaart/scripts/inventory_landkaart.py` (unit tests in `tests/`).
