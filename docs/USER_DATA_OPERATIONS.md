# User-data documentatie (buiten repo)

Canonieke operationele docs staan onder **`%USERPROFILE%\data\`** en in profielen. De repo bevat de **bron van waarheid voor scripts**; user-data docs moeten dezelfde entrypoints noemen.

## Bestanden (handmatig synchroon houden)

| Bestand | Doel |
| ------- | ---- |
| `%USERPROFILE%\data\STATUS.md` | Dagelijks overzicht, launchers, volgende stappen |
| `%USERPROFILE%\data\RECOVERY.md` | Herstel, upstream update, taakbalk |
| `%LOCALAPPDATA%\hermes\profiles\core\KANBAN_WORKFLOWS.md` | Kanban-orchestratie (profiel core) |

Na wijzigingen in `windows\UPDATE_HERMES.bat`, `FIX_TASKBAR_ICONS.bat` of `UPSTREAM_SYNC.md`: controleer of bovenstaande bestanden dezelfde paden tonen.

## Windows — vaste entrypoints

| Taak | Commando |
| ---- | -------- |
| Upstream / fork update | `windows\UPDATE_HERMES.bat` |
| Na `git pull` (andere machine of na grote wijziging) | `windows\POST_GIT_PULL.bat` |
| Taakbalk-iconen | `windows\FIX_TASKBAR_ICONS.bat` |
| Snelkoppelingen vernieuwen | `windows\REFRESH_TASKBAR_SHORTCUTS.bat` |

**Taakbalk:** pin altijd via `Hermes - * - naar taakbalk slepen.lnk` in `windows\`, niet door `.bat` te slepen (cmd-H-icoon).

**Iconen per rol (`.lnk` → `IconLocation`):**

| Rol | Bestand | Kleur |
|-----|---------|-------|
| Start, RAG | `hermes_logo.ico` | Goud |
| Setup | `hermes_logo_setup.ico` | Groen |
| Update | `hermes_logo_update.ico` | Oranje (sterk vs. goud) |
| Backup | `hermes_logo_backup.ico` | Roze |
| Restore | `hermes_logo_restore.ico` | Cyaan |

Geen `hermes_taskbar_white.ico` in snelkoppelingen (H-stub in Explorer). Na wijziging: `FIX_TASKBAR_ICONS.bat` + F5 in Explorer.

## Eenmalig na oude pin (UPDATE toont H)

1. Rechtsklik UPDATE op taakbalk → **Losmaken van de taakbalk**
2. `windows\Hermes - update - naar taakbalk slepen.lnk` → rechtsklik → **Vastmaken aan taakbalk**
3. Of: `FIX_TASKBAR_ICONS.bat` en stap 1–2 als het icoon niet ververst

Daarna vernieuwt elke geslaagde `UPDATE_HERMES.bat` de `.lnk` en icooncache automatisch.

## IDE (Cursor / VS Code)

Workspace met repo als submap: zie `docs/IDE_VSCODE_SETTINGS.example.json` (PSScriptAnalyzer-pad naar `windows/PSScriptAnalyzerSettings.psd1`).

Repo-docs: `windows/README.md`, `windows/UPSTREAM_SYNC.md`, `windows/INSTITUTIONAL.md`.
