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

## Launch-profielen (canoniek)

Alle env-defaults staan in **`windows\launch_profiles.ps1`** (één bron). `start_hermes.bat` past het gekozen profiel toe vóór `launch_hermes.bat`.

| Profiel | Entrypoint | Gedrag |
| ------- | ---------- | ------ |
| **minimal** (standaard) | `start_hermes.bat` | Snel naar chat; geen Docker/SOUL/institutioneel/dashboard bij start |
| **full** | `start_hermes_full.bat` of `start_hermes.bat --full` | SOUL, institutioneel, trust, Docker-check, dashboard (9119) |

**Resolutie** (welk profiel als je alleen `start_hermes.bat` draait):

1. Vlag `--full` / `--minimal` / `--profile:full`
2. Omgeving `HERMES_LAUNCH_PROFILE`
3. `%LOCALAPPDATA%\hermes\preferences\launch_profile`
4. `config.yaml` → `windows.launch_profile: minimal|full`
5. Anders: **minimal**

**Standaard profiel wijzigen (persistent):**

```bat
windows\set_launch_profile.bat full
```

**Eenmalig volledig:**

```bat
start_hermes_full.bat
rem of
start_hermes.bat --full
```

Handmatige env-vars (`set HERMES_MINIMAL_LAUNCH=0`) zijn niet meer nodig; overrides vóór `start_hermes.bat` blijven mogelijk (worden niet overschreven tenzij je het profiel opnieuw toepast).

**Let op:** `--minimal` / `--full` zijn **alleen** vlaggen voor `start_hermes.bat` (launch-profiel). Ze worden **niet** aan `hermes chat` doorgegeven. Voor volledige start: `start_hermes_full.bat` of `start_hermes.bat --full`.

## Snelkoppelingen (bureaublad / taakbalk)

| Wat | Hoe |
| --- | --- |
| Alles vernieuwen | `hermes_onderhoud.bat` of `windows\CREATE_DESKTOP_SHORTCUT.bat` |
| Alleen .lnk | `hermes_onderhoud.bat -ShortcutsOnly` |
| Start Hermes (snel) | `Start Hermes - naar taakbalk slepen.lnk` → WT + `start_hermes.bat` (profiel **minimal**) |
| Start Hermes (volledig) | `Start Hermes (volledig) - naar taakbalk slepen.lnk` → WT + `start_hermes_full.bat` |
| Bureaublad | `Hermes Agent.lnk` (minimal); `Hermes Agent (volledig).lnk`; optioneel `Hermes Agent (met logo).lnk` |
| Taakbalk-pin | Oude pin verwijderen → opnieuw vastmaken via `.lnk` in `windows\` (niet `.bat` slepen) |

**Start-.lnk** gebruikt `Set-HermesStartShellShortcut` (`wt.exe -M` + `cmd /k call start_hermes.bat`). Overige taken (setup, backup, RAG, …) blijven `cmd.exe /c` naar het betreffende `.bat`.

Fout na onderhoud: `. was unexpected` → `HERMES_ONDERHOUD.bat` bijgewerkt; draai `CREATE_DESKTOP_SHORTCUT.bat` opnieuw.

## Gerelateerde scripts

| Script | Wanneer |
| ------ | ------- |
| `start_hermes_debug.bat` | Fouten debuggen (`pause`, `HERMES_DEBUG_LAUNCH=1`) |
| `windows\launch_hermes.bat` | Direct starten (zonder env-defaults van root) |
| `windows\OPEN_SETUP.bat` | Eerste config (`%LOCALAPPDATA%\hermes\config.yaml`) |
| `windows\SETUP_HERMES.bat` | Volledige installatie |
| `windows\RESET_TERMINAL.bat` | Console volledig resetten |
| `windows\FIX_MOUSE_BLOCKED.bat` | Muisklik titelbalk herstellen |
| `windows\CREATE_DESKTOP_SHORTCUT.bat` | Bureaublad + taakbalk-.lnk regenereren |

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
