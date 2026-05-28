# Hermes op Windows — terminal & kleuren

## Symptoom

Hermes TUI toont **blauw/cyaan** waar je **goud/oranje** verwacht (logo en accenten). Venstertitel: `Administrator: cmd` of gewone **Command Prompt**.

## Oorzaak

De legacy **cmd.exe**-console ondersteunt geen betrouwbare **24-bit TrueColor** ANSI. Hermes (Rich) stuurt `38;2;r;g;b`-codes; cmd interpreteert kanalen vaak als **BGR** → rood en blauw omgewisseld.

Dit is geen skin-config en geen Hermes-bug in je fork; het is een **terminal-capability**-probleem.

## Oplossing (aanbevolen)

| Prioriteit | Actie |
| ---------- | ----- |
| 1 | Start via **`windows\launch_hermes.bat`** of **`start_hermes_split.bat`** (niet een losse `cmd` met handmatig `python cli.py`). |
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
  → run_hermes_prepare.ps1       (conda/python, launch state)
  → hermes_chat.cmd              (zelfde cmd, Win32-safe)
  → python -m hermes_cli.main
```

`start_hermes.bat` zet o.a.:

| Variabele | Standaard | Effect |
| --------- | --------- | ------ |
| `HERMES_MAX_FLAG=1` | aan | Geen dubbele relaunch-flits |
| `HERMES_AUTO_WINDOWS_TERMINAL=1` | aan | Start in Windows Terminal (`wt.exe`) |
| `HERMES_MINIMAL_LAUNCH=1` | aan | Sla Docker/SOUL/institutioneel over → direct chat (minder console-rommel) |
| `HERMES_SKIP_DOCKER_ON_START=1` | aan | Geen `docker info` / WSL-spawn bij start |
| `HERMES_SKIP_DASHBOARD_ON_START=1` | aan | Geen dashboard op poort 9119 bij start |
| `HERMES_CONSOLE_LAYOUT=maximized` | aan | Venster op werkgebied (taakbalk zichtbaar) |

**Volledige launcher** (bootstrap + SOUL + institutioneel + dashboard): `set HERMES_MINIMAL_LAUNCH=0` vóór start.

**Maximaliseren:** één keer vóór chat in `launch_hermes.bat` (niet handmatig opnieuw — dat veroorzaakt ghost-overlays). **QuickEdit** uit via `HermesShellCommon.ps1` + `hermes_cli.win32_console`. **Config:** eenmalig `windows\OPEN_SETUP.bat` → `%LOCALAPPDATA%\hermes\config.yaml`.

Of dubbelklik **windows\Hermes_met_logo.bat** / taakbalk-start (na `FIX_TASKBAR_ICONS.bat`).

**Niet** `start_hermes_split.bat` voor normaal gebruik — dat opent chat + log-paneel (debug).

### Kleuren (goud, niet blauw)

Standaard skin is **`default`** (goud/kawaii). Als je **blauw/cyaan** ziet, staat vaak `display.skin: slate` in config (team-default was slate).

```bat
windows\APPLY_TEAM_DISPLAY.bat

Bij **start** (`start_hermes.bat` → `launch_hermes.bat`): volgorde — (1) SOUL anatomy deploy (`launch_soul_anatomy_deploy.ps1`, skip via `HERMES_SKIP_SOUL_DEPLOY_ON_START`), (2) institutioneel runtime (`launch_institutional_runtime.ps1`, skip via `HERMES_SKIP_INSTITUTIONAL_RUNTIME`), (3) **pending trust-nazorg** (`launch_pending_trust_runtime.ps1` als `pending_trust_runtime.json` bestaat; skip via `HERMES_SKIP_PENDING_TRUST_ON_START=1`), (4) Hermes runtime. Institutioneel roept `apply_team_display.ps1` aan wanneer repo-defaults nieuwer zijn dan de stamp **of** runtime drift detecteert. Geen E2E tenzij `--institutional-e2e`. Handmatig: `APPLY_TEAM_DISPLAY.bat` alleen bij skip institutional of directe `cli.py`-start.
```

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
| **Al in Hermes-chat (WT)** | `/profile use <naam>` | **Primair (automatisch):** Toont een bevestigingsmodal $\rightarrow$ wijzigt sticky default $\rightarrow$ sluit TUI netjes af $\rightarrow$ start automatisch een schone Hermes-sessie in het geselecteerde profiel (zonder handmatige herstart). |
| **Nieuwe sessie vanuit Git Bash / WT** | `core` of `legal` of `trading` | **Directe shell wrappers:** Start direct een specifiek profiel op via de native wrappers in `~/.local/bin/` (bijv. `legal chat`, `trading`, `core`). |
| **Sticky default zonder chat** | `windows\SWITCH_PROFILE.bat <naam>` | **Scripting / CLI fallback:** `hermes profile use` met `--fix-hermes-home`, API-sync (Windows), gateway-restart indien de oude gateway draaide. |
| **Taak delegeren zonder wisselen** | `/kanban create --assign <naam>` | **Kanban-delegatie:** Maak een taak aan en delegeer deze aan een ander profiel. De dispatcher start dat profiel autonoom op de achtergrond. U hoeft zelf niet te wisselen! |

**Voortgang in chat (3 stappen):** Na bevestigen: (1) profiel opgeslagen, (2) terminal opgeschoond, (3) Hermes start op (spinner op Windows, 5–15 s).

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

**Muisklik geblokkeerd (minimaliseren/sluiten/titelbalk):** **niet handmatig opnieuw maximaliseren** na start. Oorzaak: `ENABLE_MOUSE_INPUT` of een ghost-console vangt klikken af. **Fix:** `windows\FIX_MOUSE_BLOCKED.bat` (reset + ghost-dismiss). In WT: **Ctrl+Shift+M** = markeermodus uit. Launcher: muismodus uit in `HermesShellCommon.ps1`; chat: `mouse_support=False` in `cli.py`.

**Scherm springt omhoog bij typen / alleen `core >` bovenaan:** viewport stond midden in de scrollbuffer, of prompt_toolkit “reserve vertical space” scrollde elke toetsaanslag. **Fix in fork:** `align_win32_viewport_to_bottom()` + osd-patch ook op Win32. **Reset:** `windows\RESET_TERMINAL.bat`, alle WT-tabbladen sluiten, opnieuw `start_hermes.bat`.

**Tekst overschrijft bovenaan / garbled bij start:** te veel echo vóór `cls` (Docker, SOUL, …). Gebruik standaard `HERMES_MINIMAL_LAUNCH=1` of `start_hermes.bat`. Oude “Session ended / Press any key”: nieuw WT-tab, geen `pause` na normale exit.

**Scroll / plakken / kopiëren in chat:** `run_hermes_prepare.ps1` + `hermes_chat.cmd` (zelfde cmd, `TERM` leeg). **Plakken:** `Ctrl+V` (Win32-klembord). **Kopiëren invoer:** **Shift+pijlen** + **Ctrl+C** (zonder selectie = onderbreken). **Scrollback:** WT-schuifbalk of markeermodus; assistant: `/copy`. Geen `mode con: lines=9000` (zwart scherm bij scroll).

**4× wslhost.exe + ollama.exe + vastlopen bij start:** `start_hermes.bat` zet standaard snelle start:

| Variabele | Effect |
| --------- | ------ |
| `HERMES_SKIP_DOCKER_ON_START=1` | Geen `docker info` / Docker Desktop → geen WSL2-spawn |
| `HERMES_SKIP_HARDWARE_PROBE=1` | Geen torch/onnx-probe bij chat-start |
| `HERMES_NO_WAKE_LOCAL_LLM=1` | Geen HTTP naar `localhost:11434` bij agent-init (voorkomt Ollama-GUI) |

Docker weer aan: `set HERMES_SKIP_DOCKER_ON_START=` vóór start. Ollama bij auxiliary-taken: start `ollama serve` in tray of verwijder `auxiliary.*` uit config. Zwart **ollama.exe**-venster = Ollama Desktop (niet Hermes); sluit via systeemvak of schakel “Launch at login” uit in Ollama.

## Problemen oplossen (checklist)

| Symptoom | Actie |
| -------- | ----- |
| Muisklik titelbalk / sluiten werkt niet | `FIX_MOUSE_BLOCKED.bat` → nieuw WT-tab → `start_hermes.bat` |
| Scherm springt bij typen | Zelfde + controleer dat je via `hermes_chat.cmd` start (niet `conda run`) |
| Blauw i.p.v. goud | Windows Terminal installeren; `display.skin: default` |
| Crash na “Launching chat” | Geen `TERM=xterm`; zie sectie TERM-footgun |
| Hang na model-banner | Banner-parser fix; gebruik `run_hermes_prepare.ps1` |
| Debug met pause bij fout | `start_hermes_debug.bat` → `hermes_runtime.log`, `hermes_launch.log` |

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

Zie ook `windows/INSTITUTIONAL.md` en `.cursor/rules/terminal-windows.mdc` (indien aanwezig).
