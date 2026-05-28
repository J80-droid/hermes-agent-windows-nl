# Hermes starten op Windows

**Dagelijks:** dubbelklik of run vanaf repo-root:

```bat
start_hermes.bat
```

Dat is een **dunne launcher** (alleen env-defaults + doorverwijzing). Alle logica zit in `windows\`.

## Startketen

```
start_hermes.bat          ← repo-root (aanbevolen entry)
  └─ launch_hermes.bat    ← WT, maximize, prepare, logs
       └─ hermes_wt_entry.cmd   (alleen als nog niet in WT)
       └─ run_hermes_prepare.ps1
       └─ hermes_chat.cmd       (zelfde cmd, Win32-safe)
            └─ python -m hermes_cli.main
```

**Niet** voor normaal gebruik: `conda run …`, losse `python cli.py` in cmd, of `start_hermes_split.bat` (debug split-pane).

## Wat `start_hermes.bat` standaard zet

| Variabele | Effect |
| --------- | ------ |
| `HERMES_MAX_FLAG=1` | Geen dubbele maximize-relaunch |
| `HERMES_AUTO_WINDOWS_TERMINAL=1` | Start in Windows Terminal (`wt.exe`) |
| `HERMES_MINIMAL_LAUNCH=1` | Direct naar chat (geen Docker/SOUL/institutioneel bij start) |
| `HERMES_SKIP_DOCKER_ON_START=1` | Geen Docker/WSL-spawn |
| `HERMES_SKIP_DASHBOARD_ON_START=1` | Geen dashboard op 9119 |
| `HERMES_SKIP_HARDWARE_PROBE=1` | Geen zware GPU-probe bij chat |
| `HERMES_NO_WAKE_LOCAL_LLM=1` | Geen Ollama-wake bij init |
| `HERMES_CONSOLE_LAYOUT=maximized` | Werkgebied maximaliseren (taakbalk blijft) |

Volledige launcher (bootstrap + SOUL + institutioneel + dashboard vóór chat):

```bat
set HERMES_MINIMAL_LAUNCH=0
start_hermes.bat
```

## Gerelateerde scripts

| Script | Wanneer |
| ------ | ------- |
| `start_hermes_debug.bat` | Fouten debuggen (`pause`, `HERMES_DEBUG_LAUNCH=1`) |
| `windows\launch_hermes.bat` | Direct starten (zonder env-defaults van root) |
| `windows\OPEN_SETUP.bat` | Eerste config (`%LOCALAPPDATA%\hermes\config.yaml`) |
| `windows\SETUP_HERMES.bat` | Volledige installatie |
| `windows\RESET_TERMINAL.bat` | Console volledig resetten |
| `windows\FIX_MOUSE_BLOCKED.bat` | Muisklik titelbalk herstellen |

## Logs

| Bestand | Inhoud |
| ------- | ------ |
| `hermes_runtime.log` | Python/runtime |
| `hermes_launch.log` | Launcher-stappen |
| `hermes_last_error.log` | Laatste fout |

## Terminal, kleuren, muisklik, exit

Zie **[TERMINAL_WINDOWS.md](TERMINAL_WINDOWS.md)** — enige uitgebreide gids voor WT, prompt_toolkit, plakken, `/exit`, scrollback.

## Meer context

- [README.md](README.md) — volledige Windows-toolkit
- [INSTITUTIONAL.md](INSTITUTIONAL.md) — display/SOUL/upstream
- [WINDOWS_REQUIREMENTS.md](WINDOWS_REQUIREMENTS.md) — WT installeren
