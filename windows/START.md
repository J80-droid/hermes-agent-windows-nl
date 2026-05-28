# Hermes starten op Windows

**Dagelijks:** dubbelklik of run vanaf repo-root:

```bat
start_hermes.bat
```

Standaard = **volledige launcher** (SOUL, institutioneel, trust, Docker-check, dashboard 9119). Alle env-defaults via `windows\launch_profiles.ps1`.

## Startketen

```
start_hermes.bat          ← repo-root (standaard profiel: full)
  └─ launch_hermes.bat    ← WT, maximize, prepare, logs
       └─ hermes_wt_entry.cmd   (alleen als nog niet in WT)
       └─ run_hermes_prepare.ps1
       └─ hermes_chat.cmd       (zelfde cmd, Win32-safe)
            └─ python -m hermes_cli.main
```

**Snel (alleen chat):** `start_hermes_minimal.bat` of `start_hermes.bat --minimal`

**Niet** voor normaal gebruik: `conda run …`, losse `python cli.py` in cmd, of `start_hermes_split.bat` (debug split-pane).

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

| Wat | Hoe |
| --- | --- |
| Vernieuwen | `windows\CREATE_DESKTOP_SHORTCUT.bat` |
| Start (volledig) | `Start Hermes - naar taakbalk slepen.lnk` |
| Start (snel) | `Start Hermes (snel) - naar taakbalk slepen.lnk` |
| Bureaublad | `Hermes Agent.lnk` (full); optioneel `Hermes Agent (snel).lnk` |

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

Zie **[TERMINAL_WINDOWS.md](TERMINAL_WINDOWS.md)** voor WT, kleuren, muisklik, `/exit`.
