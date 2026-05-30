# Windows Terminal: titelbalk / muisklik — overlay-fix (productie)

**Status:** opgelost en geverifieerd (2026-05-30). Deze push herstelt minimize/maximize/sluiten op de Windows Terminal-titelbalk en voorkomt regressie bij volgende starts.

**Canonieke referentie:** [TERMINAL_WINDOWS.md](TERMINAL_WINDOWS.md) (dagelijks gebruik). Dit document legt **oorzaak, symptomen, code-paden en verificatie** vast voor maintainers en support.

---

## Symptomen (wat gebruikers zagen)

| Symptoom | Wat het leek |
| -------- | ------------ |
| Minimize / maximize / sluiten op titelbalk reageert niet | “Muis kapot” |
| Muisklik in chat werkt soms niet / geen scroll | Overlay of markeermodus |
| Extra cmd- of WT-tabbladen, lege tabs | Verkeerde subprocess-launchers |
| Browser opent `http://127.0.0.1:9119/sessions` | `HERMES_DASHBOARD_OPEN_PATH=/sessions` in full-profiel |
| Zwart **ollama.exe**-venster | `HERMES_NO_WAKE_LOCAL_LLM=0` wekte Ollama Desktop |

De gele cirkel op screenshots rond de vensterknoppen = klikken kwamen **niet** bij Windows Terminal aan; een onzichtbaar venster ving ze af.

---

## Root cause (technisch)

### 1. `ExpandConsoleToWorkArea` in Windows Terminal (hoofdoorzaak titelbalk)

`launch_hermes.bat` riep vóór chat `Invoke-HermesExpandConsoleWindow` aan. Bij layout `maximized` (default) doet dat:

```text
GetConsoleWindow() → SetWindowPos(venster op volledig werkgebied, HWND_TOP)
```

Ook wanneer de gebruiker **Windows Terminal** gebruikt (`WT_SESSION` gezet), blijft `GetConsoleWindow()` het **conhost**-HWND teruggeven. Dat venster werd op schermgrootte gezet en lag als **onzichtbare laag boven de WT-chrome** — precies waar minimize/maximize/close zitten.

Dit is de klassieke **ghost overlay** uit [TERMINAL_WINDOWS.md](TERMINAL_WINDOWS.md); niet QuickEdit alleen, niet prompt_toolkit-muis alleen.

### 2. Regressies na launch-wijzigingen (2026-05-29)

| Regressie | Effect |
| --------- | ------ |
| `start /B` of `start "" powershell` voor deferred dashboard | Extra conhost/WT-tab |
| `DismissGhost` op `CASCADIA_HOSTING_WINDOW_CLASS` | Lege WT-tabs, focus kwijt |
| `HERMES_DISMISS_GHOST_CONSOLES=1` standaard in launcher | WT werd ten onrechte geminimaliseerd |
| Meerdere `Invoke-HermesRepairConsoleForChat` + expand in WT | Overlay opnieuw gelegd |
| `HERMES_DASHBOARD_OPEN_PATH=/sessions` | Browser opent automatisch |

### 3. Wat **niet** de hoofdoorzaak was

- `mouse_support=False` in `cli.py` (Win32) — correct en ongewijzigd nodig
- Alleen markeermodus — wel secundair (**Ctrl+Shift+M**)
- Dashboard op 9119 zelf — alleen overlay als verkeerd gelanceerd (geen `USE_NOWINDOW`, browser-path)

---

## Oplossing (deze push)

### Kernfix: geen work-area-expand in WT

| Component | Gedrag na fix |
| --------- | ------------- |
| `Test-HermesWindowsTerminalSession` | `WT_SESSION`, `WT_PROFILE_ID`, `WT_PROFILE_NAME` |
| `Invoke-HermesExpandConsoleWindow` | In WT: **geen** `SetWindowPos` work-area; alleen scrollbuffer + `ConfigureConsoleInputForScroll` |
| Legacy **cmd** (geen WT) | Work-area expand blijft beschikbaar |

### Herstel bestaande overlay

| API / script | Functie |
| ------------ | ------- |
| `RestoreConsoleFromWorkAreaOverlay()` | Als conhost ≥72% werkgebied: `ShowWindow(SW_RESTORE)` |
| `Invoke-HermesFixMouseBlocked` | Dashboard stop, VT-reset, QuickEdit uit, ghost-dismiss (env), Python `configure_interactive_console` |
| `FIX_MOUSE_BLOCKED.bat` | Roept `Invoke-HermesFixMouseBlocked` aan |
| `RESET_TERMINAL.bat` | Alias → zelfde keten als FIX_MOUSE |

### Launch-keten (canoniek)

```text
start_hermes.bat
  → wt.exe -M … hermes_wt_entry.cmd   (WT_SESSION)
  → launch_hermes.bat :run_agent
       → Invoke-HermesExpandConsoleWindow   (GEEN work-area in WT)
  → launch_hermes.ps1 → orchestrator (7 stappen)
  → run_hermes_prepare.ps1
       → Start-HermesDashboardAfterChatDetached (CreateNoWindow, geen browser)
  → hermes_chat.cmd
       → alleen Python: release_terminal_capture + configure_interactive_console
  → cli.py (Win32: mouse_support=False; geen align viewport in WT)
```

### Dashboard / browser

| Variabele | Default na fix |
| --------- | -------------- |
| `HERMES_DASHBOARD_USE_NOWINDOW` | `1` |
| `HERMES_SKIP_DASHBOARD_BROWSER` | `1` |
| `HERMES_DASHBOARD_OPEN_PATH` | leeg (geen auto `/sessions`) |
| `HERMES_DASHBOARD_AFTER_CHAT` | `1` (dashboard na chat, niet pre-chat stap 8) |
| `HERMES_NO_WAKE_LOCAL_LLM` | `1` (geen Ollama Desktop-popup) |

Deferred dashboard: `Start-HermesDashboardAfterChatDetached` → `Start-HermesNoWindowProcess` (geen `start /B`, geen `start "" powershell`).

### Ghost-dismiss

- Alleen `ConsoleWindowClass` (niet WT `CASCADIA_HOSTING_WINDOW_CLASS`)
- `HERMES_DISMISS_GHOST_CONSOLES=1` **alleen** in `FIX_MOUSE_BLOCKED.bat`, niet standaard in `launch_hermes.bat`

---

## Gebruiker: recovery playbook

1. Sluit **alle** Hermes / cmd / WT-tabbladen.
2. `windows\FIX_MOUSE_BLOCKED.bat` of `windows\RESET_TERMINAL.bat`
3. `start_hermes.bat` (controleer WT in titelbalk, niet alleen losse cmd).
4. Klik minimize/maximize/close op **WT-titelbalk** (niet op zwart chatvlak).
5. Chat nog vast? **Ctrl+Shift+M** (markeermodus uit).

Isolatie dashboard:

```bat
set HERMES_SKIP_DASHBOARD_ON_START=1
start_hermes.bat
```

---

## Automatische tests (geen live WT-muis)

| Test | Wat het bewijst |
| ---- | --------------- |
| `tests/windows/test_launch_dashboard_on_start.py::test_mouse_regression_contracts` | Geen `start /B`, NoWindow, geen repair in `hermes_chat.cmd`, WT-expand guard |
| `tests/windows/test_critical_windows_scripts.py` | Prepare/chat-keten |
| `tests/cli/test_cli_windows_mouse.py` | `mouse_support=False` op Win32 |
| `tests/windows/test_launch_profiles.py` | Geen auto browser-open in profiel |

**Niet** vertrouwen op `RUN_LAUNCH_UI_SINK_E2E` alleen — geen live muisklik in WT.

---

## Bestanden in deze fix (maintainer-index)

| Bestand | Wijziging |
| ------- | --------- |
| `HermesShellCommon.ps1` | `RestoreConsoleFromWorkAreaOverlay`, `Test-HermesWindowsTerminalSession`, `Invoke-HermesFixMouseBlocked`, `Start-HermesDashboardAfterChatDetached`, WT-skip expand, Cascadia uit dismiss |
| `launch_hermes.bat` | Geen standaard `HERMES_DISMISS_GHOST_CONSOLES`; `HERMES_SKIP_DASHBOARD_BROWSER=1` |
| `hermes_chat.cmd` | Alleen Python console-prep |
| `run_hermes_prepare.ps1` | Deferred dashboard NoWindow; geen `Clear-Host` |
| `launch_profiles.ps1` | Geen `/sessions` browser; `NO_WAKE=1` |
| `cli.py` | Geen `align_win32_viewport_to_bottom` in WT |
| `FIX_MOUSE_BLOCKED.bat` / `RESET_TERMINAL.bat` | Geünificeerde recovery |
| `HermesLaunchUi.ps1` | `Write-HermesLaunchPinnedHeader` (UX, los van muis) |
| `scripts/Start-HermesDashboardAfterChat.ps1` | Nieuw, deferred start |

---

## Git / release note

**Commit message (samenvatting):** fix(windows): WT titelbalk-muis — geen ExpandConsoleToWorkArea in WT, overlay-herstel, dashboard NoWindow zonder browser.

**Deze push lost op:** onzichtbare conhost-overlay op WT-titelbalk (minimize/maximize/close), extra vensters door verkeerde dashboard-launchers, automatische browser naar `/sessions`.
