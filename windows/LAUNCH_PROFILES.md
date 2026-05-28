# Windows launch-profielen

Canonieke implementatie: [`launch_profiles.ps1`](launch_profiles.ps1). Gebruikersgids: [`START.md`](START.md).

## Profielen

| Profiel | Entrypoint | Gedrag |
| ------- | ---------- | ------ |
| **full** (standaard) | `start_hermes.bat` | SOUL deploy, institutioneel runtime, pending trust, Docker-check, dashboard (9119), daarna chat |
| **minimal** | `start_hermes_minimal.bat` of `start_hermes.bat --minimal` | Direct chat; skips pre-chat-fases |

`start_hermes_full.bat` is een alias voor profiel **full** (zelfde als `start_hermes.bat`).

## Resolutievolgorde

1. CLI: `--full`, `--minimal`, `--profile:full`
2. Omgeving: `HERMES_LAUNCH_PROFILE`
3. Bestand: `%LOCALAPPDATA%\hermes\preferences\launch_profile` (één regel: `full` of `minimal`)
4. Config: `windows.launch_profile` in `%LOCALAPPDATA%\hermes\config.yaml`
5. Default: **full**

```cmd
windows\set_launch_profile.bat full
windows\set_launch_profile.bat minimal
```

## Niet doorgeven aan `hermes chat`

Vlaggen `--minimal` / `--full` zijn **alleen** voor `start_hermes.bat`. Ze worden gefilterd vóór `python -m hermes_cli.main` (`Get-HermesLaunchCliArgs`).

## Snelkoppelingen

Na wijziging: `CREATE_DESKTOP_SHORTCUT.bat` of `hermes_onderhoud.bat -ShortcutsOnly`.

| .lnk | Profiel |
| ---- | ------- |
| Start Hermes - naar taakbalk slepen.lnk | full |
| Start Hermes (snel) - naar taakbalk slepen.lnk | minimal |
| Hermes Agent.lnk (bureaublad) | full |
| Hermes Agent (snel).lnk | minimal |

## Tests

```cmd
pytest tests\windows\test_launch_profiles.py -q
```
