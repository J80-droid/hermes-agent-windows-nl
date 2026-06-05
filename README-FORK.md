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
| One-command installateur | `scripts/windows/install-J..ps1` | Volledige installatie in een commando |
| Update-script | `scripts/windows/update-J..ps1` | Conflictvrije updates met keuzemenu |
| Aangepaste uninstaller | `hermes_cli/uninstall.py` | Herinstallatie-URL verwijst naar deze fork |
| Profiel-model overerving | `hermes_cli/profile_model_inheritance.py` | Eén model in root config voor alle `-p <profiel>`-sessies |
| Profielwissel (productie) | `hermes_cli/profile_switch.py`, `cli.py`, `relaunch.py`, `windows/SWITCH_PROFILE*.bat` | Eén kern voor chat, CLI en scripts: `-p` override, root-`HERMES_HOME`, API-sync, gateway-handoff, E2E-audit |
| RAG + profiel-docs (NL) | `docs/README.md`, `docs/PROFILE_MODEL_INHERITANCE.md` | Index, twee fasen, centraal model |
| Core orchestrator routing | `docs/ORCHESTRATOR_ROUTING.md`, `docs/templates/SOUL_CORE_ORCHESTRATOR.md` | Routing-matrix + repo-template core SOUL |
| Landkaart (completeness) | `skills/productivity/landkaart/` | `/landkaart`, inventarisatie vóór diepgang |
| Runtime SOUL backup/restore | `windows/backup_soul_profiles.ps1`, `restore_from_backup.ps1` | Manifest v2: `localappdata_hermes/`; `-RestoreRuntimePersonas` |
| Legal domein (lenzen, één bucket) | `docs/LEGAL_DOMAIN_ARCHITECTURE.md`, `LEGAL_TAXONOMY.md` | Rechtsgebied-lenzen; audit `RUN_LEGAL_DOMAIN_E2E.bat` |
| Domein-toolsets (token-besparing) | `docs/DOMAIN_TOOLSET_AUDIT.md`, `docs/domain_toolsets.yaml` | Minimale toolbox per profiel; opt-in via agent; `SYNC_DOMAIN_TOOLSETS.bat` |
| WT titelbalk-muis (overlay-fix) | `windows/MOUSE_OVERLAY_FIX.md`, `FIX_MOUSE_BLOCKED.bat` | Geen conhost work-area expand in `WT_SESSION`; geverifieerd 2026-05-30; tag `windows-wt-titlebar-mouse-2026-05-30` |
| **Nous 100% intact + dunne overlay** | `overlay/`, `docs/NOUS_OVERLAY_ARCHITECTURE.md` | Tier A = upstream; fork via `overlay/bootstrap.py` + runtime patches; drift `Test-NousTreeIdentical.ps1` |

### Nous overlay (institutioneel, 2026-06)

Upstream Python/UI in Tier A blijft **ongewijzigd** na `SYNC_NOUS`. Fork-features:

- **Bootstrap:** `overlay/bootstrap.py` laadt `overlay/hermes_cli/*` en patchet o.a. statusbalk-kosten, `/cost`, Gemini-pricing.
- **Sync:** `windows\SYNC_NOUS.bat` — merge + overlay + strict drift-gate.
- **Herstel Tier A:** `windows\scripts\Invoke-RestoreNousTierA.ps1` vóór drift-test.
- **E2E:** `audits\RUN_NOUS_OVERLAY_INSTITUTIONAL_E2E.bat` (8 stappen: drift, harness, verify, smokes, pytest).
- **Unit:** `pytest tests/overlay/test_bootstrap.py`

Zie [`docs/NOUS_OVERLAY_ARCHITECTURE.md`](docs/NOUS_OVERLAY_ARCHITECTURE.md) en [`docs/NOUS_DRIFT_BASELINE.md`](docs/NOUS_DRIFT_BASELINE.md).

### Windows Terminal — titelbalk-muis (2026-05-30)

**Probleem (opgelost):** onzichtbare conhost-overlay blokkeerde minimize/maximize/sluiten in Windows Terminal.

- **Start:** `start_hermes.bat` (niet rechtstreeks `launch_hermes.bat` in losse cmd).
- **Recovery:** `windows\FIX_MOUSE_BLOCKED.bat` → alle tabs dicht → opnieuw `start_hermes.bat`.
- **Docs:** [`windows/MOUSE_OVERLAY_FIX.md`](windows/MOUSE_OVERLAY_FIX.md), [`windows/TERMINAL_WINDOWS.md`](windows/TERMINAL_WINDOWS.md).
- **Code-fix:** commit `91955c651`; poort: `windows\audits\RUN_WT_MOUSE_OVERLAY_E2E.bat`.

### Profielwissel (productie)

- **In chat:** `/profile use legal` → bevestiging → 3 stappen feedback → `legal ❯`
- **CLI:** `hermes profile use legal --fix-hermes-home` (flags: `--sync-env`, `--restart-gateway`, `--restart-chat`)
- **Windows:** `windows\SWITCH_PROFILE.bat legal` of `SWITCH_PROFILE_AND_CHAT.bat`
- **Audit:** `windows\audits\RUN_PROFILE_SWITCH_E2E.bat`
- **Check:** `windows\scripts\verify_hermes_home.ps1` (User-`HERMES_HOME` = root, geen `profiles\core`)

### Wat NIET is aangepast (Tier A)

- `cli.py` — geen inline fork-hooks voor statusbalk of `/cost` (alleen via `overlay/hermes_cli/cli_*_patch.py`)
- `hermes_cli/status_bar_cost.py` (upstream-pad) — vervangen door overlay-shim met dezelfde module-naam na bootstrap
- `web/src`, `ui-tui/src` — alleen tijdelijk tijdens `build_fork_ui_assets.ps1`; daarna `git checkout` Tier A

### Beperkte Tier A-diffs (beleid, niet feature-dump)

- `hermes_cli/main.py` — sticky `active_profile` + `profile use` waar nodig
- Overige fork-logica: **`overlay/`** + `windows/` + geladen shims (`profile_switch`, `usage_snapshot`, …)

---

## Installatie

### Nieuwe gebruiker (Windows 10/11)

Open **PowerShell** en draai:

```powershell
irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/install-J..ps1 | iex
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
| **Nous + overlay (drift-gate)** | `windows\SYNC_NOUS.bat` | Merge upstream + overlay + `Test-NousTreeIdentical` — zie `docs/NOUS_OVERLAY_ARCHITECTURE.md` |
| **Primair (Windows fork)** | `windows\UPDATE_HERMES.bat` | Preflight + Nous-merge + RAG + verify (`.ps1`, geen pause in keten) |
| **Alternatief** | `irm .../update-J..ps1 \| iex` | Keuzemenu bij lokale wijzigingen |
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

## CI en GitHub-notificaties

| Workflow | Op deze fork |
| -------- | ------------ |
| **Fork Windows Institutional** | Draait op elke push/PR naar `main` (Windows, legal pytest, H1–H14) |
| **Tests** (upstream Linux-matrix) | **Uitgeschakeld** op `J80-droid/hermes-agent-windows-nl` — die suite is bedoeld voor upstream op Ubuntu en faalt vaak op fork-drift (CLI/RAG/padnamen) |

Na een push naar `main` zie je vooral **Fork Windows Institutional** in Actions. Minder e-mail: GitHub → Settings → Notifications → Actions → alleen *Failed workflows* of watch-level voor deze repo verlagen.

Bij upstream-merge: conflict in `.github/workflows/tests.yml` oplossen door de regel `if: github.repository != 'J80-droid/hermes-agent-windows-nl'` op jobs `test`, `rag`, `e2e` en `save-durations` te behouden.

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
