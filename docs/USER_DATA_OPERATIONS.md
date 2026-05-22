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
| Upstream / fork update | `windows\UPDATE_HERMES.bat` (verify in keten via `.ps1`, geen pause — zie `windows\UPSTREAM_SYNC.md`) |
| Na `git pull` (andere machine of na grote wijziging) | `windows\POST_GIT_PULL.bat` |
| Taakbalk-iconen | `windows\FIX_TASKBAR_ICONS.bat` |
| Snelkoppelingen vernieuwen | `windows\REFRESH_TASKBAR_SHORTCUTS.bat` |
| Setup (logica) | `scripts\windows\setup_hermes_windows.ps1` — **niet** volledig kopiëren naar `windows\` |
| Setup (dubbelklik) | `windows\SETUP_HERMES.bat` — standaard wizard; `--files-only` = alleen bestanden |

**Setup PS1:** alleen `scripts/windows/setup_hermes_windows.ps1` bewerken; `windows/setup_hermes_windows.ps1` blijft wrapper. Keten controleren: handmatig `VERIFY_WINDOWS_CHAIN.bat`; in `UPDATE_HERMES.bat` automatisch via `verify_windows_script_chain.ps1`.

**Taakbalk:** pin altijd via `Hermes - * - naar taakbalk slepen.lnk` in `windows\`, niet door `.bat` te slepen (cmd-H-icoon).

**Iconen per rol (`.lnk` → `IconLocation`):**

| Rol | Bestand | Kleur |
|-----|---------|-------|
| Start, RAG | `hermes_logo.ico` | Goud |
| Setup, Open Setup | `hermes_logo_setup.ico` | Groen |
| Update | `hermes_logo_update.ico` | Wit/zilver monogram |
| Backup | `hermes_logo_backup.ico` | Roze |
| Restore | `hermes_logo_restore.ico` | Cyaan |

Geen `hermes_taskbar_white.ico` in snelkoppelingen (H-stub in Explorer).

**Geen logo / alleen letter H / wit document-icoon:** bron-PNG ontbrak in `assets\` (staat vaak in `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`). Herstel:

```bat
conda run -n hermes-env python windows/tools/generate_colored_hermes_icons.py
windows\FIX_TASKBAR_ICONS.bat
```

Daarna **F5** in `windows\`. De generator kopieert de PNG naar `assets\Hermes_logo.png` en bouwt **7-lagen** `.ico` (16–256 px).

**Icoon = wit document in Verkenner (oude pin):** losmaken en opnieuw `.lnk` uit `windows\` vastmaken.

**Technisch:** `windows\*.lnk` gebruiken `cmd.exe /c` + icoon uit `%LOCALAPPDATA%\Hermes\shortcut-icons\` (kopie van `windows\hermes*.ico`). Verify waarschuwt bij kapotte 1-laags ICO (onder 8 KB).

## Eenmalig na oude pin (UPDATE toont H)

1. Rechtsklik UPDATE op taakbalk → **Losmaken van de taakbalk**
2. `windows\Hermes - update - naar taakbalk slepen.lnk` → rechtsklik → **Vastmaken aan taakbalk**
3. Of: `FIX_TASKBAR_ICONS.bat` en stap 1–2 als het icoon niet ververst

Daarna vernieuwt elke geslaagde `UPDATE_HERMES.bat` de `.lnk` en icooncache automatisch.

## IDE (Cursor / VS Code)

Workspace met repo als submap: zie `docs/IDE_VSCODE_SETTINGS.example.json` (PSScriptAnalyzer-pad naar `windows/PSScriptAnalyzerSettings.psd1`).

Repo-docs: `windows/README.md`, `windows/UPSTREAM_SYNC.md`, `windows/INSTITUTIONAL.md`.
