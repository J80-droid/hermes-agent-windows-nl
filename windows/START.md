# Hermes starten op Windows

**Dagelijks (aanbevolen — één script):** taakbalk of repo-root:

```bat
start_hermes.bat
```

Gedrag:

1. **Achter `origin` (tracking branch)?** → `git pull` + `POST_GIT_PULL` + Hermes-relaunch in WT.
2. **Up-to-date?** → direct normale start (geen pull, geen extra wachttijd behalve korte `git fetch`).
3. **Merge bezig / echte uncommitted wijzigingen / offline?** → pull overslaan, gewoon starten. **Alleen** `assets/Hermes_logo.png` + `windows/hermes*.ico` na taakbalk-fix telt als schoon (zelfde als UPDATE).

**Handmatig forceren:**

| Vlag | Effect |
|------|--------|
| `--pull` | Altijd pull + sync (ook als up-to-date) |
| `--pull -Full` | Zelfde + AutoRepair + InstitutionalVerify |
| `--sync` | Alleen POST (na handmatige `git pull`) |
| `--no-pull` | Geen auto-pull deze keer |

Uitzetten auto-pull permanent: `set HERMES_SKIP_AUTO_PULL_ON_START=1`. Geen fetch bij start: `set HERMES_SKIP_FETCH_ON_START=1`.

`PULL_HERMES.bat` = `start_hermes.bat --pull`. Draai **niet** in het Hermes-tabblad dat wordt afgesloten.

`--sync -SkipRelaunch`: POST zonder Hermes-herstart; wist `.update_check` cache. Start daarna opnieuw met `start_hermes.bat`.

Standaard = **volledige launcher** (SOUL, institutioneel, trust, Docker-check, dashboard 9119). Alle env-defaults via `windows\launch_profiles.ps1`.

### Sessie-onderhoud (automatisch)

| Wanneer | Wat |
|---------|-----|
| **Start (full)** | Snelkoppeling verify/fix, TUI rebuild indien stale, config-drift **waarschuwing**, model auto-repair |
| **Na pull** | POST: trust/SOUL/drift strict; daarna PostPullTail (toolsets, LanceDB, TUI, pins, optioneel RAG) |
| **Na relaunch** | Stamp `post_pull_maintenance` voorkomt dubbele TUI/pin-work (~15 min, zelfde commit) |

| Env (full default) | Effect |
|--------------------|--------|
| `HERMES_SKIP_SHORTCUT_MAINT_ON_START=1` | Geen .lnk verify/fix bij start |
| `HERMES_SKIP_TUI_MAINT_ON_START=1` | Geen ui-tui build bij start |
| `HERMES_AUTOREPAIR_MODEL_ON_DRIFT=1` | Provider/catalog repair bij start (full profiel) |
| `HERMES_RAG_ON_POST_PULL=1` | Forceer RAG na pull |
| `HERMES_RAG_ON_POST_PULL_SMART=1` | RAG alleen bij bronnen + gewijzigde domains (default aan) |
| `HERMES_AUTO_COMMIT_BRANDING=1` | Auto-commit alleen iconen na pin-fix (opt-in) |

**Verificatie na wijzigingen:**

```bat
audits\RUN_SESSION_MAINTENANCE_E2E.bat
powershell -NoProfile -ExecutionPolicy Bypass -File windows\tests\HermesSessionMaintenance.Unit.Tests.ps1
pytest tests\windows\test_hermes_session_maintenance.py tests\audits\test_session_maintenance_e2e_harness.py -q -m "not e2e"
```

## Startketen

```
start_hermes.bat          ← repo-root (standaard profiel: full)
  └─ launch_hermes.bat    ← WT, maximize, logs
       └─ scripts/launch_hermes.ps1  ← Launch UI Sink, --setup, env-info
            └─ launch_pre_chat_orchestrator.ps1  (bootstrap, SOUL, institutional, trust, dashboard)
       └─ run_hermes_prepare.ps1
       └─ hermes_chat.cmd
            └─ python -m hermes_cli.main
```

**Snel (alleen chat):** `start_hermes_minimal.bat` of `start_hermes.bat --minimal`

**Niet** voor normaal gebruik: `conda run …`, losse `python cli.py` in cmd, of `start_hermes_split.bat` (debug split-pane).

## Titelbalk / muisklik (opgelost)

**Status:** geverifieerd werkend (2026-05-30). Volledige uitleg: **[MOUSE_OVERLAY_FIX.md](MOUSE_OVERLAY_FIX.md)**.

| Symptoom | Actie |
| -------- | ----- |
| Minimize / maximize / sluiten reageert niet | `windows\FIX_MOUSE_BLOCKED.bat` of `windows\RESET_TERMINAL.bat` |
| Daarna | **Alle** Hermes/cmd/WT-tabbladen sluiten |
| Opnieuw starten | Alleen **`start_hermes.bat`** (titel moet **Windows Terminal** zijn, niet alleen cmd) |
| Klikken | Op de **WT-titelbalk**, niet op het zwarte chatvlak |
| Chat vast | **Ctrl+Shift+M** (markeermodus uit) |

Automatische poort (pytest + checklist): `windows\audits\RUN_WT_MOUSE_OVERLAY_E2E.bat`.

## Launch-profielen

| Profiel | Entrypoint | Gedrag |
| ------- | ---------- | ------ |
| **full** (standaard) | `start_hermes.bat` | SOUL, institutioneel, trust, Docker, dashboard |
| **minimal** | `start_hermes_minimal.bat` of `--minimal` | Direct chat, lichte start |

**Resolutie** (als je alleen `start_hermes.bat` draait):

1. Vlag `--full` / `--minimal` / `--profile:…`
2. `HERMES_LAUNCH_PROFILE` (env)
3. `%LOCALAPPDATA%\hermes\preferences\launch_profile`
4. `config.yaml` → `windows.launch_profile`
5. Anders: **full**

**Persistent vastleggen:**

```bat
windows\set_launch_profile.bat full
```

**Eenmalig snel:**

```bat
start_hermes_minimal.bat
```

Profielvlagen `--minimal` / `--full` zijn **alleen** voor `start_hermes.bat`, niet voor `hermes chat`.

## Snelkoppelingen

**Canonieke gids:** **[TAAKBALK_PINS.md](TAAKBALK_PINS.md)** (drie lagen, rollen, troubleshooting).

| Wat | Waar / hoe |
| --- | ---------- |
| Dubbelklik (repo) | `windows\Start Hermes - naar taakbalk slepen.lnk` (full), `(snel)` voor minimal |
| **Taakbalk vastmaken (eenmalig)** | `%LOCALAPPDATA%\Hermes\taakbalk\` → `Hermes Start.lnk`, … — **niet** slepen uit `windows\` |
| Map openen | `windows\OPEN_HERMES_TAAKBALK_PINS.bat` |
| Vernieuwen / bureaublad | `windows\CREATE_DESKTOP_SHORTCUT.bat` |
| Na update / start | Pins automatisch (`fix_hermes_taskbar_pins.ps1`); handmatig: `FIX_TASKBAR_ICONS.bat` |

| Symptoom | Actie |
| -------- | ----- |
| Venstertitel is alleen **cmd**, geen Windows Terminal | `CREATE_DESKTOP_SHORTCUT.bat` + `FIX_TASKBAR_ICONS.bat`; taakbalk alleen opnieuw vastmaken vanuit **`taakbalk\`** |
| Minimize werkt niet na oude sessie | `FIX_MOUSE_BLOCKED.bat` → alle tabs dicht → `start_hermes.bat` |
| Na `git pull` | Full start repareert pins; anders `FIX_TASKBAR_ICONS.bat` |
| Kapotte-pin-pop-up | `HERSTEL_TAAKBALK_POPUP.bat` of Ja → opnieuw vastmaken uit `taakbalk\` |

Zie ook **[TERMINAL_WINDOWS.md](TERMINAL_WINDOWS.md)** (wt.exe + `cmd /c call`).

## Gerelateerde scripts

| Script | Wanneer |
| ------ | ------- |
| `start_hermes_debug.bat` | Fouten debuggen |
| `start_hermes_full.bat` | Alias full (zelfde als standaard) |
| `start_hermes_minimal.bat` | Snelle chat-start |
| `windows\OPEN_SETUP.bat` | Eerste config |
| `windows\CREATE_DESKTOP_SHORTCUT.bat` | Snelkoppelingen regenereren |

## Logs

| Bestand | Inhoud |
| ------- | ------ |
| `hermes_runtime.log` | Python/runtime |
| `hermes_launch.log` | Launcher-stappen |
| `hermes_last_error.log` | Laatste fout |

Zie **[TERMINAL_WINDOWS.md](TERMINAL_WINDOWS.md)** voor WT, kleuren, muisklik, `/exit`. Titelbalk-overlay (opgelost): **[MOUSE_OVERLAY_FIX.md](MOUSE_OVERLAY_FIX.md)**.
