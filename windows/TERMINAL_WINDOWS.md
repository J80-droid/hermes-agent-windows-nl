# Hermes op Windows — terminal & kleuren

## Symptoom

Hermes TUI toont **blauw/cyaan** waar je **goud/oranje** verwacht (logo en accenten). Venstertitel: `Administrator: cmd` of gewone **Command Prompt**.

## Oorzaak

De legacy **cmd.exe**-console ondersteunt geen betrouwbare **24-bit TrueColor** ANSI. Hermes (Rich) stuurt `38;2;r;g;b`-codes; cmd interpreteert kanalen vaak als **BGR** → rood en blauw omgewisseld.

Dit is geen skin-config en geen Hermes-bug in je fork; het is een **terminal-capability**-probleem.

## Oplossing (aanbevolen)

| Prioriteit | Actie |
| ---------- | ----- |
| 1 | Start via **`start_hermes.bat`** (repo-root) → `windows\launch_hermes.bat`. Niet losse `cmd` + `python cli.py`. Zie [START.md](START.md). |
| 2 | **Windows Terminal** is verplicht (`wt.exe`). Zie [`requirements-windows.txt`](requirements-windows.txt) / [`INSTALL_WINDOWS_TERMINAL.bat`](INSTALL_WINDOWS_TERMINAL.bat). `start_hermes.bat` start automatisch in WT (`HERMES_AUTO_WINDOWS_TERMINAL=1`). |
| 3 | Gebruik **conda `hermes-env`** (canoniek via `HermesPythonPolicy.ps1` / `REPAIR_PYTHON.bat`). |

**Windows Terminal + Anaconda Prompt** is de combinatie die je beschreef — correct.

### Snelste pad (authentieke chat, één paneel)

```bat
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
start_hermes.bat
```

**Startketen (2026-05):**

```
start_hermes.bat
  → windows\launch_hermes.bat  (WT via hermes_wt_entry.cmd indien nodig)
  → scripts\launch_hermes.ps1  (Launch UI Sink, env-info, --setup)
  → launch_pre_chat_orchestrator.ps1  (bootstrap, SOUL, institutional, trust, dashboard)
  → run_hermes_prepare.ps1       (conda/python, launch state)
  → hermes_chat.cmd              (zelfde cmd, Win32-safe)
  → python -m hermes_cli.main
```

`start_hermes.bat` zet o.a.:

| Variabele | Standaard | Effect |
| --------- | --------- | ------ |
| `HERMES_MAX_FLAG=1` | aan | Geen dubbele relaunch-flits |
| `HERMES_AUTO_WINDOWS_TERMINAL=1` | aan | Start in Windows Terminal (`wt.exe`) |
| `HERMES_MINIMAL_LAUNCH=0` | standaard (full) | SOUL, institutioneel, Docker, dashboard bij start |
| `HERMES_MINIMAL_LAUNCH=1` | alleen met `--minimal` / `start_hermes_minimal.bat` | Direct chat |
| `HERMES_SKIP_DOCKER_ON_START=1` | aan | Geen `docker info` / WSL-spawn bij start |
| `HERMES_SKIP_DASHBOARD_ON_START=1` | aan | Geen dashboard op poort 9119 bij start |
| `HERMES_DASHBOARD_OPEN_PATH` | *(standaard leeg)* | Alleen zetten om browser te openen (bv. `/codebase-viz`); standaard **geen** tab |
| `HERMES_SKIP_DASHBOARD_BROWSER` | `1` in launcher/profiel | Geen automatische browser bij dashboard-start |
| `HERMES_MINIMAL_LAUNCH=1` / snel-profiel | aan | Dashboard wordt **niet** gestart |
| `HERMES_CONSOLE_LAYOUT=maximized` | aan | Legacy cmd: venster op werkgebied; **in WT geen** conhost work-area expand (zie [MOUSE_OVERLAY_FIX.md](MOUSE_OVERLAY_FIX.md)) |

**Snelle launcher** (alleen chat): `start_hermes_minimal.bat` of `start_hermes.bat --minimal`. Standaard is **volledig** via `start_hermes.bat` (zie `launch_profiles.ps1`).

**Maximaliseren:** één keer vóór chat in `launch_hermes.bat` — **niet** in Windows Terminal (`WT_SESSION`): `ExpandConsoleToWorkArea` op conhost geeft een onzichtbare fullscreen overlay op de titelbalk (minimize/maximize/close werken niet). In WT alleen QuickEdit/muis uit; grootte regelt WT zelf. Legacy cmd: work-area expand wel. **QuickEdit** uit via `HermesShellCommon.ps1` + `hermes_cli.win32_console`. **Config:** eenmalig `windows\OPEN_SETUP.bat` → `%LOCALAPPDATA%\hermes\config.yaml`.

Of dubbelklik **`windows\Start Hermes - naar taakbalk slepen.lnk`** of bureaublad **`Hermes Agent.lnk`** (beide → `start_hermes.bat` in WT). Optioneel: `Hermes Agent (met logo).lnk` (ASCII-logo, daarna dezelfde startketen). Na wijzigingen: `CREATE_DESKTOP_SHORTCUT.bat`; taakbalk-pin opnieuw vastmaken.

**Niet** `start_hermes_split.bat` voor normaal gebruik — dat opent chat + log-paneel (debug).

### Kleuren (goud, niet blauw)

Standaard skin is **`default`** (goud/kawaii). Als je **blauw/cyaan** ziet, staat vaak `display.skin: slate` in config (team-default was slate).

```bat
windows\APPLY_TEAM_DISPLAY.bat
```

**Standaard** (`start_hermes.bat`, profiel **full**): SOUL → institutioneel → trust → Docker-check → dashboard → chat. **Snelle start:** `start_hermes_minimal.bat` of `start_hermes.bat --minimal` (geen pre-chat-fases). Handmatig display: `APPLY_TEAM_DISPLAY.bat`.

of: `hermes config set display.skin default` — daarna Hermes opnieuw starten.

### Markdown in antwoordpanelen (### koppen, **vet:**)

Twee lagen (niet door elkaar halen):

| Laag | Waar | Kleur |
| ---- | ---- | ----- |
| **Hermes UI** | Banner, prompt, status | Skin **`default`** (goud) — `display.skin` |
| **Assistant-antwoord** | LLM-tekst in panel/stream | **`institutional_rich`** + `assistant_palette: demo` (cyaan/groen/magenta/geel) |

Team-defaults in `windows/team_display.defaults`: `assistant_render_style=institutional_rich`, `assistant_palette=demo`, `assistant_label_columns=true`, `streaming=false`, `compact=false`, **`show_cost=true`**, **`cost_bar_mode=rich`**. Framework-defaults in `hermes_cli/config.py` en gateway matchen dit (**TUI én klassieke CLI** statusbalk: rich `$turn / $session │ cw/out/in/cr │ calls │ tools`; altijd zichtbaar bij `/cost on` — fallback `n/a`/`included`/`~NK tok`; tijdens stream in TUI **`~$turn`** of live tokens; `/cost` = zichtbaarheid; `config.set cost_bar_mode minimal|toggle` = formaat; geen `/costbar`-slash).

Code: `hermes_cli/institutional_render.py`, `hermes_cli/display_markdown.py` (`get_assistant_console_theme()`; `prepare_assistant_markdown_plain(..., realign_tables=…)` — institutional eindpaneel skipt tabel-realign), gateway `agent/rich_output.py`. Statusbalk-kosten: `hermes_cli/usage_snapshot.py` + **`hermes_cli/status_bar_cost.py`** (klassieke CLI) + TUI `ui-tui/src/domain/usageCostBar.ts` (`statusRuleColumns` + `resolveStatusRuleLayout` — effectieve breedte minus composer-padding; kosten in accent vóór cwd), `ui-tui/src/domain/liveTurnCost.ts`, `ui-tui/src/components/appChrome.tsx`; toggle `/cost`. **Throughput (tok/s):** `hermes_cli/status_bar_throughput.py` + TUI `statusBarThroughput.ts` — segment **na** cost (`NN tok/s`, stijl `status-bar-tps` / `theme.color.statusTps`, gedimd wit `#A8A8A8`); agent `record_agent_stream_delta` / `finalize_agent_call_tps`; toggle `/tps` (`display.show_status_bar_tps`, default **aan**; verborgen &lt; 76 cols); audits **`RUN_STATUS_BAR_THROUGHPUT_E2E.bat`**, **`RUN_STATUS_BAR_COST_E2E.bat`** (TUI), **`RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat`** (klassieke CLI). **Na TUI-wijzigingen:** `windows/REBUILD_TUI.bat` + Hermes **volledig** herstarten (draaiende sessie laadt geen nieuwe `dist/entry.js`). Klassieke CLI (`hermes chat` zonder `--tui`): statusbalk via `cli.py` `_get_status_bar_fragments()` — **breed (≥76 cols):** `⚕ model │ ctx │ [bar] % │ duur │ prompt-timer` (`26s`, geen emoji; `display.show_prompt_timer_emoji`, `/timer-emoji`) `│ $kosten` (gedimd blauw `status-bar-cost`) `│ NN tok/s` (`status-bar-tps` / `#A8A8A8`) `│ breakdown │ N calls │ N tools`; post-merge: `python scripts/verify_fork_status_bar_display.py`. tool-teller via `agent.session_tool_executions`; eindpaneel via `ChatConsole(theme=get_assistant_console_theme())`; tijdens stream (met `streaming=false`) ruwe markdown, Rich pas op het eindpaneel.

Legacy: `assistant_render_style: markdown_legacy` → goud via `skin_markdown_theme()`. Upstream Rich-default (magenta) geldt alleen zonder deze fork-instellingen.

Globale typografie: `docs/INSTITUTIONAL_PRESENTATION.md` + `SYNC_SOUL_SNIPPETS.bat`.

### API-keys (twee Hermes-homes)

Als `HERMES_HOME=%LOCALAPPDATA%\hermes` maar keys alleen in `%USERPROFILE%\.hermes\.env` staan → Gemini **HTTP 400 invalid API key**.

Hermes kiest vaak **`credential_pool` vóór `.env`** (`credential_pool_strategies: gemini: fill_first`). Een kapotte pool-entry in `profiles\core\auth.json` (bv. `access_token: "N"`) geeft dezelfde 400, ook als `.env` goed is.

```bat
windows\SYNC_HERMES_API_ENV.bat
```

Kopieert `GOOGLE_API_KEY` naar root `.env`, werkt alle `profiles\*\.env` bij, en roept daarna `fix_gemini_credential_pool.ps1` aan.

| Script | Doel |
| ------ | ---- |
| `APPLY_TEAM_DISPLAY.bat` | Handmatig display op **alle profielen**; normaal automatisch via start/update |
| `APPLY_INSTITUTIONAL_RUNTIME.bat` | display + SOUL + E2E (handmatig of `-NoE2E`) |
| `SYNC_HERMES_API_ENV.bat` | API-keys + `OBSIDIAN_VAULT_PATH`/`WIKI_PATH` naar alle profiel-`.env` + Gemini pool |
| `FIX_GEMINI_CREDENTIAL_POOL.bat` | Alleen pool in `auth.json` (root + profielen) herstellen |
| `audits\RUN_STATUS_BAR_COST_E2E.bat` | TUI statusbalk-kosten E2E (rich, 10 stappen) |
| `audits\RUN_STATUS_BAR_COST_E2E.bat -ApplyDisplayFix` | Zelfde + display sync vóór audit |
| `audits\RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.bat` | Klassieke CLI statusbalk-kosten E2E (12 stappen, incl. live post-turn + Gemini cache) |
| `audits\RUN_AUDITS.bat -IncludeStatusBarCostE2E` | TUI statusbalk E2E in gecombineerde poort |
| `audits\RUN_AUDITS.bat -IncludeClassicCliStatusBarCostE2E` | Klassieke CLI statusbalk E2E in gecombineerde poort |
| `audits\RUN_CODEBASE_SMOKE_E2E.bat` | Codebase smoke E2E (E1/E2, geen E3); zie `docs/CODEBASE_AUDIT_EVIDENCE.md` |
| `audits\RUN_CODEBASE_SMOKE_AUDIT.bat` | Alleen smoke-runner (sneller) |
| `POST_GIT_PULL.bat -IncludeCodebaseSmoke` / `-IncludeCodebaseSmokeE2E` | Optionele smoke na pull (~32s / ~45s) |
| `UPDATE_HERMES.bat -IncludeCodebaseSmoke` / `-IncludeCodebaseSmokeE2E` | Optionele smoke na upstream post-merge |
| `audits\RUN_AUDITS.bat -IncludeCodebaseSmokeE2E` | Codebase smoke E2E in gecombineerde poort |
| `SWITCH_PROFILE.bat <naam>` | Sticky profiel + API-sync + `HERMES_HOME`-fix + gateway (indien actief) |
| `SWITCH_PROFILE_AND_CHAT.bat <naam>` | Zelfde + direct `hermes chat -p <naam>` |
| `audits\RUN_PROFILE_SWITCH_E2E.bat` | E2E-audit profielwissel (pytest + scripts) |

### Profiel wisselen (Drie lagen)

De fork biedt drie verschillende manieren om flexibel en robuust van profiel te wisselen, afhankelijk van uw context:

| Situatie / Context | Aanbevolen Methode | Werking & Details |
| :--- | :--- | :--- |
| **Al in Hermes-chat (WT)** | `/profile use <naam>` | **Primair:** TUI-modal in composer (`1`/`2` of ↑/↓ + Enter) $\rightarrow$ sticky default $\rightarrow$ TUI-exit $\rightarrow$ sync/gateway $\rightarrow$ herstart `chat` met `legal ❯` (geen `⟳ Opstarten` in prompt; zie `docs/PROFILE_SWITCH.md`). |
| **Nieuwe sessie vanuit Git Bash / WT** | `core` of `legal` of `trading` | **Directe shell wrappers:** Start direct een specifiek profiel op via de native wrappers in `~/.local/bin/` (bijv. `legal chat`, `trading`, `core`). |
| **Sticky default zonder chat** | `windows\SWITCH_PROFILE.bat <naam>` | **Scripting / CLI fallback:** `hermes profile use` met `--fix-hermes-home`, API-sync (Windows), gateway-restart indien de oude gateway draaide. |
| **Taak delegeren zonder wisselen** | `/kanban create --assign <naam>` | **Kanban-delegatie:** Maak een taak aan en delegeer deze aan een ander profiel. De dispatcher start dat profiel autonoom op de achtergrond. U hoeft zelf niet te wisselen! |

**Voortgang in chat (3 stappen):** Na bevestigen: (1) profiel opgeslagen, (2) terminal opgeschoond, (3) Hermes start op (spinner op Windows, 5–15 s).

**Windows in-chat (2026-05-30):** `/profile use` gebruikt hetzelfde bevestigingspaneel als `/new` (UI-thread, geen verborgen stdin). Zware stappen lopen met spinner + timeouts (`HERMES_PROFILE_SYNC_TIMEOUT`, `HERMES_PROFILE_SWITCH_TIMEOUT`). Zie `docs/PROFILE_SWITCH_WINDOWS_AUDIT.md`.

**Vlaggen behouden / strippen:** Bij de in-chat `/profile use` herstart worden storende flags (zoals `-p` of `--profile`) automatisch gestript; het child-proces krijgt expliciet `-p <naam>` en root-`HERMES_HOME`. Om alleen sticky te zetten zonder herstart: `/profile use <naam> --no-restart`.

**HERMES_HOME (User):** Moet `%LOCALAPPDATA%\hermes` (root) zijn, **niet** `...\profiles\core`. Controle: `windows\scripts\verify_hermes_home.ps1`. Installatie corrigeert profiel-subdirs automatisch.

**Gateway / API na wissel:** In-chat en `SWITCH_PROFILE` herstarten de gateway alleen als die op het oude profiel draaide. API-keys: automatische sync via `sync_hermes_api_env.ps1` (Windows). Kanban-workers op het oude profiel lopen door tot ze klaar zijn.

**Fout `\ufeffcore`:** `active_profile` per ongeluk met PowerShell `Set-Content -Encoding UTF8` geschreven (BOM). De in-chat `/profile use` en `SWITCH_PROFILE.bat` schrijven BOM-safe. Gebruik bij voorkeur deze tools in plaats van handmatige edities met BOM. Bij een crash: herstel het bestand door `/profile use <naam>` opnieuw te gebruiken of `SWITCH_PROFILE.bat <naam>` te draaien.

## TERM-footgun (prompt_toolkit / chat-crash)

**Symptoom:** venster sluit direct na "Launching Hermes Agent Chat…" met `NoConsoleScreenBufferError` / *Found xterm-256color, while expecting a Windows console*.

**Oorzaak:** `TERM=xterm-256color` (of `COLORTERM` + Unix-TERM) in een **echte** Windows-console (cmd / Windows Terminal). prompt_toolkit kiest dan geen `Win32Output` → crash.

**Fix in deze fork (structureel):**

| Onderdeel | Gedrag |
| --------- | ------ |
| `launch_hermes.bat` | Zet **geen** `TERM=xterm-256color` meer bij `WT_SESSION` |
| `run_hermes_prepare.ps1` | `Set-HermesWin32ChatEnv` (wist TERM/COLORTERM, houdt `FORCE_COLOR` + VT) |
| `hermes_chat.cmd` | Chat in **dezelfde cmd**; `set TERM=` vóór Python |
| Kleuren / markdown | ONGEWIJZIGD — via `FORCE_COLOR`, `enable_console_ansi.ps1`, `display_markdown.py` |

**Debug:** `start_hermes_debug.bat` (sneller, `pause` bij fout) → logs: `hermes_runtime.log`, `hermes_launch.log`, `hermes_last_error.log`.

**Hang na config-pad (model-banner):** nooit `(?ms)` + `.*` op hele `config.yaml` — gebruikt `Get-HermesModelFieldsFromConfigYaml` (regelscanner). Dashboard bij start: `HERMES_DASHBOARD_QUICK_START=1` (geen 100s /health-wacht).

**Muisklik geblokkeerd (minimaliseren/sluiten/titelbalk):** **OPGELOST (2026-05-30)** — zie **[MOUSE_OVERLAY_FIX.md](MOUSE_OVERLAY_FIX.md)** (volledige root cause + verificatie). Kort: in **Windows Terminal** mag `ExpandConsoleToWorkArea` **niet** (onzichtbare conhost-overlay op titelbalk). Recovery: `FIX_MOUSE_BLOCKED.bat` of `RESET_TERMINAL.bat` → alle tabs dicht → `start_hermes.bat`. **Ctrl+Shift+M** = markeermodus uit. Chat: `mouse_support=False`; QuickEdit/muis uit via `HermesShellCommon.ps1` + `win32_console.py`.

**Scherm springt omhoog bij typen / alleen `core >` bovenaan:** viewport stond midden in de scrollbuffer, of prompt_toolkit “reserve vertical space” scrollde elke toetsaanslag. **Fix in fork:** `align_win32_viewport_to_bottom()` + osd-patch ook op Win32. **Reset:** `windows\RESET_TERMINAL.bat`, alle WT-tabbladen sluiten, opnieuw `start_hermes.bat`.

**Tekst overschrijft bovenaan / garbled bij start:** vroeger door gemengde cmd/PS-echo vóór `cls` en live subprocess-output tijdens capture. **Fix (Launch UI Sink):** pre-chat output loopt via `Write-HermesLaunchUi` + `HermesLaunchUi.ps1` (EL `[2K` per regel); zware subprocessen naar log tijdens capture. Entry: `launch_hermes.bat` → `scripts/launch_hermes.ps1` → `launch_pre_chat_orchestrator.ps1` (bootstrap **in** orchestrator, geen `-SkipBootstrap` in bat). Wil je alleen chat: `start_hermes_minimal.bat`. Oude “Session ended / Press any key”: nieuw WT-tab, geen `pause` na normale exit.

| Variabele | Effect |
| --------- | ------ |
| `HERMES_LAUNCH_UI` | `auto` (default): rich in WT, normal in cmd, quiet bij redirect |
| `HERMES_LAUNCH_UI=quiet` | Alleen log + stapresultaten; geen live detail |
| `HERMES_LAUNCH_UI=verbose` | Alle detailregels op console |
| `HERMES_LAUNCH_VISUAL=0` | Geen spinner/checklist-animatie (tekst-only stappen) |
| Rich visual (spinner/checklist) | Alleen met `WT_SESSION`; goudgele kopregel `[33m` (geen dubbele titel op spinner); verstreken tijd per tiende seconde (50 ms tick) |
| `HERMES_SKIP_LAUNCH_BOOTSTRAP_FAST_PATH=1` | Stap 2/7 altijd volledig (`ensure_*` + RAG-check); geen `launch_bootstrap.json` fast-path |
| `HERMES_DASHBOARD_AFTER_CHAT` | Default `1`: dashboard start **na** chat via `Start-HermesDashboardAfterChat.ps1` (pre-chat 7 stappen). Oud: `=0` |
| `HERMES_DASHBOARD_USE_NOWINDOW` | Default `1`: dashboard zonder conhost (voorkomt onzichtbare muisklik-overlay) |
| Muisklik vast / geen scroll | `windows\FIX_MOUSE_BLOCKED.bat` of `RESET_TERMINAL.bat`; in chat: **Ctrl+Shift+M** (markeermodus uit). Geen extra `powershell`-repair in `hermes_chat.cmd` (alleen Python `configure_interactive_console`). |
| Ghost overlay / muisklik geblokkeerd | Geen dubbele `Invoke-HermesExpandConsoleWindow`; `Stop-HermesGhostInputBlockers` vóór start; zie `FIX_MOUSE_BLOCKED.bat` |
| `HERMES_LAUNCH_VERBOSE=1` | Subprocess-detail ook op console tijdens capture |

E2E: `audits\RUN_LAUNCH_UI_SINK_E2E.bat` (8/8). Zie `audits/LAUNCH_UI_SINK_E2E_README.md`.

**Dashboard (9119) na chat:** standaard niet meer als pre-chat stap 8; `hermes_chat.cmd` start `windows\scripts\Start-HermesDashboardAfterChat.ps1` op de achtergrond zodra Python-chat draait.

**Stap 8 (dashboard) traag of spinner blijft hangen (alleen bij `HERMES_DASHBOARD_AFTER_CHAT=0`):** `pip install -e .[web]` draait **niet** elke start — alleen bij gewijzigde `pyproject.toml` / Codebase Viz `package.json` of ontbrekend manifest (`%LOCALAPPDATA%\hermes\web-dashboard-deps.json`). Pygount pre-warm alleen als `output\research\codebase_viz_pygount_cache.json` ontbreekt of ongeldig is (bijv. pytest-temp in `repo_path`). **Repair:** `windows\FIX_CODEBASE_VIZ_CACHE.bat`. Workspace-dev: dashboard wordt **niet** herstart als deps, dist, pygount-cache en poort 9119 al OK zijn.

| Variabele | Effect |
| --------- | ------ |
| `HERMES_FORCE_DASHBOARD_PIP=1` | Forceer pip `[web]` bij start |
| `HERMES_CODEBASE_VIZ_PREGOUNT_CACHE=skip` | Geen blokkerende pygount pre-warm |
| `HERMES_CODEBASE_VIZ_SKIP_BUILD=1` | Geen `npm run build` voor Codebase Viz dist |

E2E optimalisaties: `audits\RUN_DASHBOARD_LAUNCH_OPTIMIZATIONS_E2E.bat`. Unit: `windows\tests\HermesWebDashboardLaunch.Unit.Tests.ps1`.

**Scroll / plakken / kopiëren in chat:** `run_hermes_prepare.ps1` + `hermes_chat.cmd` (zelfde cmd, `TERM` leeg). **Plakken:** `Ctrl+V` (Win32-klembord). **Kopiëren invoer:** **Shift+pijlen** + **Ctrl+C** (zonder selectie = onderbreken). **Scrollback:** WT-schuifbalk of markeermodus; assistant: `/copy`. Geen `mode con: lines=9000` (zwart scherm bij scroll).

**4× wslhost.exe + ollama.exe + vastlopen bij start:** standaard **full** start draait Docker-check. Snelle start zonder Docker/WSL-spawn: `start_hermes_minimal.bat`. Of vóór start:

| Variabele | Effect |
| --------- | ------ |
| `HERMES_SKIP_DOCKER_ON_START=1` | Geen `docker info` / Docker Desktop → geen WSL2-spawn |
| `HERMES_SKIP_HARDWARE_PROBE=1` | Geen torch/onnx-probe bij chat-start |
| `HERMES_NO_WAKE_LOCAL_LLM=1` | Geen HTTP naar `localhost:11434` bij agent-init (voorkomt Ollama-GUI) |

Ollama bij auxiliary-taken: start `ollama serve` in tray of verwijder `auxiliary.*` uit config. Zwart **ollama.exe**-venster = Ollama Desktop (niet Hermes); sluit via systeemvak of schakel “Launch at login” uit in Ollama.

## Productie-fix titelbalk-muis (2026-05-30)

**Status: geverifieerd werkend.** Documentatie: [MOUSE_OVERLAY_FIX.md](MOUSE_OVERLAY_FIX.md).

| Check na pull | Verwacht |
| ------------- | -------- |
| Start via `start_hermes.bat` | Venster heet **Windows Terminal** (of WT-tab met cmd-host) |
| Titelbalk minimize/close | Werkt op **WT-chrome**, niet alleen in zwart vlak |
| Geen auto-browser | Geen tab naar `127.0.0.1:9119/sessions` tenzij je `HERMES_DASHBOARD_OPEN_PATH` zet |
| `git log -1` | `fix(windows):` WT titelbalk-muis / overlay |

---

## Regressies na launch-wijzigingen (2026-05-29)

Recente launch-UI- en deferred-dashboard-wijzigingen kunnen het bewezen muis-contract breken. Controleer vóór nieuwe “muis-fixes”:

| Symptoom / regressie | Oorzaak | Herstel (canoniek) |
| -------------------- | ------- | ------------------ |
| Overlay op titelbalk / geen scroll | `start /B` of `start "" powershell` voor deferred dashboard (extra conhost/WT-tab) | `Start-HermesDashboardAfterChatDetached` → `Start-HermesNoWindowProcess` + `HERMES_DASHBOARD_USE_NOWINDOW=1` |
| Lege WT-tabbladen / derde venster | `DismissGhost` minimaliseerde `CASCADIA_HOSTING_WINDOW_CLASS` | Alleen `ConsoleWindowClass` ghost-cmd minimaliseren |
| Extra `ollama.exe`-venster | `HERMES_NO_WAKE_LOCAL_LLM=0` in full-profiel | Standaard `1`; alleen `HERMES_ALLOW_WAKE_LOCAL_LLM=1` om te wekken |
| Gele titel verdwijnt tijdens stappen | `Clear-Host` in prepare/launch bij WT of spinner zonder vaste kop | Geen `Clear-Host` in `run_hermes_prepare.ps1`; in `launch_hermes.bat`/`hermes_wt_entry.cmd` alleen buiten `WT_SESSION`; `Write-HermesLaunchPinnedHeader` in `HermesLaunchUi.ps1` |
| Dubbele fullscreen cmd | Tweede `Invoke-HermesExpandConsoleWindow` of `Invoke-HermesEnsureInteractiveConsole` → `start /max cmd /k` (alleen zonder Win32-buffer; normaal WT-pad triggert dit niet) | Start via `start_hermes.bat` / `hermes_wt_entry.cmd`; eén expand in `launch_hermes.bat`; vermijd handmatig maximaliseren |
| Ghost minimaliseren “te agressief” | `HERMES_DISMISS_GHOST_CONSOLES=1` standaard in launcher | **Niet** standaard in `launch_hermes.bat` (alleen `FIX_MOUSE_BLOCKED.bat`); anders minimaliseert WT zichzelf |
| Scroll lijkt dood (viewport onderaan) | `align_win32_viewport_to_bottom` bij chat-start | Scroll via WT-schuifbalk; markeermodus: **Ctrl+Shift+M** |

**Handmatige verificatie:** zie checklist hieronder (`FIX_MOUSE_BLOCKED.bat` → WT → `start_hermes.bat`). **Automatisch:** `windows\audits\RUN_WT_MOUSE_OVERLAY_E2E.bat` (pytest + handmatige stappen); `test_mouse_regression_contracts`, `test_expand_console_to_work_area_guarded_in_wt`, `test_cli_align_viewport_skipped_in_wt`. **Niet** vertrouwen op `RUN_LAUNCH_UI_SINK_E2E` alleen — geen live WT/muisklik.

## Problemen oplossen (checklist)

| Symptoom | Actie |
| -------- | ----- |
| Muisklik titelbalk / sluiten werkt niet | `FIX_MOUSE_BLOCKED.bat` → nieuw WT-tab → `start_hermes.bat` |
| Dashboard start minuten / pygount elke keer | `FIX_CODEBASE_VIZ_CACHE.bat`; check `web-dashboard-deps.json`; zie stap 8 hierboven |
| Scherm springt bij typen | Zelfde + controleer dat je via `hermes_chat.cmd` start (niet `conda run`) |
| Na exit: chat kwijt | Scrollback blijft; scroll omhoog om na te lezen. Volledig leeg: `RESET_TERMINAL.bat` |
| Na exit: ghost statusbalk | `finalize_console_after_chat` zet alleen muismodi/renderer terug |
| Blauw i.p.v. goud | Windows Terminal installeren; `display.skin: default` |
| Crash na “Launching chat” | Geen `TERM=xterm`; zie sectie TERM-footgun |
| Hang na model-banner | Banner-parser fix; gebruik `run_hermes_prepare.ps1` |
| Debug met pause bij fout | `start_hermes_debug.bat` → `hermes_runtime.log`, `hermes_launch.log` |

## Launch-console (geen door elkaar lopende regels)

`launch_pre_chat_orchestrator.ps1` zet per fase `HERMES_LAUNCH_CAPTURE_CONSOLE=1`. Zware subprocessen (o.a. `fix_hermes_taskbar_pins.ps1`, `rebuild_tui.ps1`, RAG-importcheck) schrijven naar een buffer; output verschijnt **na** de stap, niet midden in `Stap N van M`. Cosmetische PyTorch-/esbuild-regels worden gefilterd. Handmatige scripts (`FIX_TASKBAR_ICONS.bat`) tonen output live zoals voorheen.

## Wat de fork al doet

- `launch_hermes.bat`: `WT_SESSION` → anders `wt -M` via `hermes_wt_entry.cmd`; console-reset + `cls` vóór chat.
- `run_hermes_prepare.ps1` + `hermes_chat.cmd`: prepare in PS, **chat in dezelfde cmd** (geen `conda run` subprocess).
- `hermes_cli/win32_console.py`: QuickEdit/muis uit, viewport naar onderkant buffer, terminal-reset bij exit.
- `cli.py` (Win32): osd-patch tegen scroll-jump, `mouse_support=False`, Ctrl+V plakken.
- `Set-HermesWin32ChatEnv`: VT via `enable_console_ansi.ps1`; **geen** Unix-`TERM`.
- `start_hermes_split.bat`: split-pane logs in WT (alleen debug).

## Uitzonderingen

| Situatie | Gedrag |
| -------- | ------ |
| Geen `wt.exe` | Waarschuwing + fallback cmd (kleuren kunnen afwijken). |
| `HERMES_SKIP_WINDOWS_TERMINAL=1` | Geen WT-relaunch (debug/CI). |
| Venstertitel **Administrator: cmd** | **UAC** opende legacy cmd (geen WT). Sinds fix: admin **niet** meer standaard; alleen met `HERMES_REQUIRE_ADMIN=1`. |
| UAC nodig (zeldzaam) | `set HERMES_REQUIRE_ADMIN=1` vóór start — probeert elevated **wt -M**. |

## Kanban / subagents

Spawnt subprocessen met `HERMES_PYTHON` / conda `hermes-env`. Zorg dat de **parent**-sessie dezelfde env heeft (WT + geactiveerde conda), niet een kale OS-`python`.

## Agent / IDE

Voor Cursor-agents: start geen Hermes TUI in geïntegreerde **cmd**-terminals voor kleurverwachting; gebruik WT of accepteer afgeweken palet.

## Resume-sessie

| Methode | Wanneer |
| ------- | ------- |
| `windows\RESUME_HERMES.bat <session_id>` | Veilig resume zonder cmd-parse-fouten |
| In lopende Hermes | `/resume` of `hermes --resume <id>` in de TUI |
| `launch_hermes.bat` met args | Alleen zonder `<` `>` `&` in tekst; anders `HERMES_LAUNCH_ARGS` (sinds fix) |

Fout `'licy' is not recognized` = kapotte cmd-regel (`\s` in pad → tab, of `<` als redirect). Geen Hermes-crash.

Zie ook [START.md](START.md), [INSTITUTIONAL.md](INSTITUTIONAL.md) en `.cursor/rules/terminal-windows.mdc` (indien aanwezig).
