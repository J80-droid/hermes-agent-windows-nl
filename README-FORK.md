# Hermes Agent — Windows (NL) Fork

**Institutionele fork van [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) met Nederlandstalige Windows-optimalisaties.**

## Over deze fork

Deze fork is de **enige goedgekeurde bron** voor Hermes-installaties binnen dit netwerk. Alle wijzigingen ten opzichte van upstream worden hier bijgehouden en getest voordat ze beschikbaar worden gesteld.

### Wat is toegevoegd ten opzichte van upstream

| Component | Locatie | Beschrijving |
| --------- | ------- | ------------ |
| Windows setup toolkit | `scripts/windows/` | Canoniek `setup_hermes_windows.ps1`; `windows/` = wrapper + launchers; taakbalk-iconen |
| RAG citatieregels | `.cursorrules` | Nederlandstalige bronvermelding en presentatie-eisen |
| Aangepaste installer | `scripts/install.ps1` | Clone deze fork i.p.v. upstream |
| One-command installateur | `scripts/windows/install-jamel.ps1` | Volledige installatie in een commando |
| Update-script | `scripts/windows/update-jamel.ps1` | Conflictvrije updates met keuzemenu |
| Aangepaste uninstaller | `hermes_cli/uninstall.py` | Herinstallatie-URL verwijst naar deze fork |
| Profiel-model overerving | `hermes_cli/profile_model_inheritance.py` | Eén model in root config voor alle `-p <profiel>`-sessies |
| Profielwissel (productie) | `hermes_cli/profile_switch.py`, `cli.py`, `relaunch.py`, `windows/SWITCH_PROFILE*.bat` | Eén kern voor chat, CLI en scripts: `-p` override, root-`HERMES_HOME`, API-sync, gateway-handoff, E2E-audit |
| RAG + profiel-docs (NL) | `docs/README.md`, `docs/PROFILE_MODEL_INHERITANCE.md` | Index, twee fasen, centraal model |

### Profielwissel (productie)

- **In chat:** `/profile use legal` → bevestiging → 3 stappen feedback → `legal ❯`
- **CLI:** `hermes profile use legal --fix-hermes-home` (flags: `--sync-env`, `--restart-gateway`, `--restart-chat`)
- **Windows:** `windows\SWITCH_PROFILE.bat legal` of `SWITCH_PROFILE_AND_CHAT.bat`
- **Audit:** `windows\audits\RUN_PROFILE_SWITCH_E2E.bat`
- **Check:** `windows\scripts\verify_hermes_home.ps1` (User-`HERMES_HOME` = root, geen `profiles\core`)

### Wat NIET is aangepast

- `hermes_cli/main.py` — alleen `profile use`-handler uitgebreid; overige logica tegen `origin/main`
- `hermes_cli/banner.py` — update-check vergelijkt tegen `origin/main`
- Alle overige Python-bestanden — identiek aan upstream

---

## Installatie

### Nieuwe gebruiker (Windows 10/11)

Open **PowerShell** en draai:

```powershell
irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/install-jamel.ps1 | iex
```

De installer regelt alles: `uv`, Python 3.11, Node.js 22, PortableGit, virtual environment, dependencies, web/TUI-assets, `hermes.cmd` shim, en User PATH.

Na installatie **een nieuw PowerShell-venster openen**. Daarna:

```powershell
hermes setup           # Configuratiewizard: model, provider, toolsets (volledige wizard)
hermes --help          # Alle beschikbare commando's
```

---

## Updates

### Update ontvangen (gebruiker)

| Methode | Commando | Beschrijving |
| ------- | -------- | ------------ |
| **Primair (Windows fork)** | `windows\UPDATE_HERMES.bat` | Preflight + Nous-merge + RAG + verify (`.ps1`, geen pause in keten) |
| **Alternatief** | `irm .../update-jamel.ps1 \| iex` | Keuzemenu bij lokale wijzigingen |
| **CLI** | `hermes update` | Ingebouwd (zelfde merge; minder post-merge Windows-stappen) |
| **Gevorderd** | `git pull` + handmatig pip | Zie `windows\UPSTREAM_SYNC.md` |

### Update uitbrengen (beheerder)

```powershell
# 1. Upstream wijzigingen binnenhalen
cd "d:\A.I\APPS\Hermes_agent_WS\hermes-agent"
git fetch upstream
git merge upstream/main

# 2. Testen of alles werkt
hermes doctor

# 3. Pushen naar fork
git push origin main
```

Gebruikers ontvangen de update via een van bovenstaande methodes.

---

## Beheer

- **GitHub**: [github.com/J80-droid/hermes-agent-windows-nl](https://github.com/J80-droid/hermes-agent-windows-nl)
- **Upstream**: [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- **Licentie**: MIT (identiek aan upstream)
- **Schrijfrechten**: Alleen beheerder — gebruikers kunnen alleen lezen en pullen

---

## Technische notities

### Data-scheiding

Hermes splitst bewust code en data:

| Wat | Locatie | In Git? |
| --- | ------- | ------ |
| Code | `%LOCALAPPDATA%\hermes\hermes-agent\` | Ja |
| Data (config, skills, geheugen, sessies) | `%LOCALAPPDATA%\hermes\` + `%USERPROFILE%\data\` (RAG) | Nee |

**Model/provider:** altijd `%LOCALAPPDATA%\hermes\config.yaml`. Profielen onder `profiles\<naam>\` bevatten MCP en toolsets, geen vast `model:` — zie `docs/PROFILE_MODEL_INHERITANCE.md`.

Bij elke update wordt alleen code overschreven. Persoonlijke data blijft altijd intact.

### Shell-commando's op Windows

Hermes voert shell-commando's uit via Git Bash (PortableGit). Resolutievolgorde:

1. `HERMES_GIT_BASH_PATH` (automatisch gezet door installer)
2. `%LOCALAPPDATA%\hermes\git\usr\bin\bash.exe`
3. Systeem Git-for-Windows
4. MSYS2/Cygwin/bash op PATH

### Dashboard beperking

Het `/chat` embedded terminal pane in de web-dashboard werkt niet op native Windows (vereist POSIX PTY). De rest van de dashboard werkt volledig.
