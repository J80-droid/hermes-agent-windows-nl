# Windows audits (optioneel)

Deze map is **optioneel**. Er is geen volledige upstream `RUN_AUDITS.ps1` in de fork.

| Runner | Doel |
| ------ | ---- |
| **`RUN_PROFILE_SWITCH_E2E.bat`** | Profielwissel E2E: `verify_hermes_home`, pytest-subset, `SWITCH_PROFILE.bat`, subprocess `-p` override, cleanup |
| **`windows\tests\RUN_PYTEST.bat`** | Brede pytest (excl. integration/e2e) |
| **`windows\VERIFY_WINDOWS_CHAIN.bat`** | Script-keten backup/RAG |

## Profielwissel E2E

```text
Dubbelklik of: windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Stappen: HERMES_HOME-root check → unit tests → `SWITCH_PROFILE.bat legal` → smoke `HERMES_HOME=profiles\core` + `-p legal` → sticky terug naar `core`.

Sync naar `%USERPROFILE%\.hermes\_local_assets\` kopieert dit README + audit-runners mee waar geconfigureerd.
