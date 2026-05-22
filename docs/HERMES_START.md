# Hermes starten (zonder conda in PATH)

Je `(venv)` in deze map is **niet** `hermes-env`. Gebruik:

## Snel (aanbevolen)

```bat
cd D:\A.I\APPS\Hermes_agent_WS
hermes.bat -p legal status
hermes.bat -p legal chat
```

Of vanuit elke map:

```bat
%USERPROFILE%\data\scripts\hermes.bat -p legal chat
```

## Eén keer PATH in deze terminal

```bat
%USERPROFILE%\data\scripts\use_hermes_env.bat
hermes -p legal chat
```

## Chat-rooktest (script)

```bat
%USERPROFILE%\data\scripts\hermes_legal_chat.bat
```

## Model en provider (geldt voor alle profielen)

Het inference-model staat **centraal**, niet in `profiles\legal\config.yaml`:

| Wat | Waar |
| --- | --- |
| Model/provider | `%LOCALAPPDATA%\hermes\config.yaml` |
| Wijzigen | `hermes.bat model` (ook met `-p legal` — schrijft naar root) |
| MCP + LanceDB-pad | `%LOCALAPPDATA%\hermes\profiles\legal\config.yaml` |

Documentatie: [PROFILE_MODEL_INHERITANCE.md](PROFILE_MODEL_INHERITANCE.md)

## Als chat faalt (401 / verkeerde provider)

1. **Root-model controleren:** `hermes.bat doctor` (zonder `-p`) of `hermes.bat -p legal doctor` (toont inherited model).
2. **Model instellen:** `hermes.bat model` — kies provider + model (één keer voor alle profielen).
3. **API-key:** in `%LOCALAPPDATA%\hermes\.env` (of profiel-`.env` voor profiel-specifieke tokens).
4. **Verouderd profiel-blok:** als `profiles\legal\config.yaml` nog `model:` bevat → `hermes.bat doctor --fix`.

**Niet meer doen:** handmatig `model: openrouter/...` in `profiles\legal\config.yaml` zetten — dat wordt genegeerd of veroorzaakt verwarring.

## SOUL.md per domein (persona)

Persona staat in de **profielroot**, niet in `memory\`:

| Profiel | SOUL.md |
| --- | --- |
| legal | `%LOCALAPPDATA%\hermes\profiles\legal\SOUL.md` |
| philosophy | `%LOCALAPPDATA%\hermes\profiles\philosophy\SOUL.md` |
| core | `%LOCALAPPDATA%\hermes\profiles\core\SOUL.md` |

Volledige tabel: [PROFILE_SOUL.md](PROFILE_SOUL.md)

```powershell
notepad "$env:LOCALAPPDATA\hermes\profiles\philosophy\SOUL.md"
hermes -p philosophy chat
```

## Fork bijwerken (Nous upstream)

```bat
D:\A.I\APPS\Hermes_agent_WS\hermes-agent\windows\UPDATE_HERMES.bat
```

Preflight, merge, RAG-postinstall en script-keten-verify zitten in het script. Verify in de keten: `verify_windows_script_chain.ps1` (geen pause); handmatig: `VERIFY_WINDOWS_CHAIN.bat` (wel pause).

| Na actie | Script |
| -------- | ------ |
| `git pull` | `windows/POST_GIT_PULL.bat` |
| Keten controleren (handmatig) | `windows/VERIFY_WINDOWS_CHAIN.bat` |
| Setup + wizard | `windows/SETUP_HERMES.bat` (standaard) of `OPEN_SETUP.bat`; alleen bestanden: `--files-only` |
| Icoon kapot / leeg in Explorer | `python windows/tools/generate_colored_hermes_icons.py` daarna `windows/FIX_TASKBAR_ICONS.bat` + F5 |
| Taakbalk-pin | Via `Hermes - * - naar taakbalk slepen.lnk` (niet `.bat` slepen) |

Setup bewerken: alleen `scripts/windows/setup_hermes_windows.ps1` (wrapper in `windows/`).

Taakbalk-iconen: goud=start/RAG, groen=setup, wit=update, roze=backup, cyaan=restore.

Zie [USER_DATA_OPERATIONS.md](USER_DATA_OPERATIONS.md) en [../windows/UPSTREAM_SYNC.md](../windows/UPSTREAM_SYNC.md).

## Meer documentatie

- Index: [README.md](README.md)
- SOUL per profiel: [PROFILE_SOUL.md](PROFILE_SOUL.md)
- RAG twee fasen: [RAG_TWEE_FASEN.md](RAG_TWEE_FASEN.md)
- Voortgang: [../memory-bank/progress.md](../memory-bank/progress.md)
