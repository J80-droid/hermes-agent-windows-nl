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
| 2 | Installeer **Windows Terminal** (`wt.exe` op PATH). De launcher herstart automatisch in WT (`wt -M`). |
| 3 | Gebruik **conda `hermes-env`** (canoniek via `HermesPythonPolicy.ps1` / `REPAIR_PYTHON.bat`). |

**Windows Terminal + Anaconda Prompt** is de combinatie die je beschreef — correct.

### Snelste pad (authentieke chat, één paneel)

```bat
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
start_hermes.bat
```

Of dubbelklik **windows\Hermes_met_logo.bat** / taakbalk-start (na `FIX_TASKBAR_ICONS.bat`).

**Niet** `start_hermes_split.bat` voor normaal gebruik — dat opent chat + log-paneel (debug).

### Kleuren (goud, niet blauw)

Standaard skin is **`default`** (goud/kawaii). Als je **blauw/cyaan** ziet, staat vaak `display.skin: slate` in config (team-default was slate).

```bat
windows\APPLY_TEAM_DISPLAY.bat

Bij **start** (`start_hermes.bat` → `launch_hermes.bat`): automatisch display + SOUL via `scripts\launch_institutional_runtime.ps1`. Die roept `apply_team_display.ps1` aan (alle keys uit `team_display.defaults`, incl. `show_cost` en `cost_bar_mode`) wanneer de repo-defaults nieuwer zijn dan de stamp **of** runtime drift detecteert. Geen E2E tenzij `--institutional-e2e`. Handmatig: `APPLY_TEAM_DISPLAY.bat` alleen nodig bij `HERMES_SKIP_INSTITUTIONAL_RUNTIME=1` of directe `cli.py`-start zonder launcher.
```

of: `hermes config set display.skin default` — daarna Hermes opnieuw starten.

### Markdown in antwoordpanelen (### koppen, **vet:**)

Twee lagen (niet door elkaar halen):

| Laag | Waar | Kleur |
| ---- | ---- | ----- |
| **Hermes UI** | Banner, prompt, status | Skin **`default`** (goud) — `display.skin` |
| **Assistant-antwoord** | LLM-tekst in panel/stream | **`institutional_rich`** + `assistant_palette: demo` (cyaan/groen/magenta/geel) |

Team-defaults in `windows/team_display.defaults`: `assistant_render_style=institutional_rich`, `assistant_palette=demo`, `assistant_label_columns=true`, `streaming=false`, `compact=false`, **`show_cost=true`**, **`cost_bar_mode=rich`**. Framework-defaults in `hermes_cli/config.py` en gateway matchen dit (TUI-statusbalk: `$turn / $session │ cw/out/in/cr │ calls │ tools`; altijd zichtbaar bij `/cost on` — fallback `n/a`/`included`/`~NK tok`; tijdens stream **`~$turn`** of live tokens; `/cost` = zichtbaarheid; `config.set cost_bar_mode minimal|toggle` = formaat; geen `/costbar`-slash).

Code: `hermes_cli/institutional_render.py`, `hermes_cli/display_markdown.py` (`get_assistant_console_theme()`), gateway `agent/rich_output.py`. TUI statusbalk-kosten: `hermes_cli/usage_snapshot.py`, `ui-tui/src/domain/usageCostBar.ts` (`resolveStatusRuleLayout` — kosten vóór cwd, niet afgekapt), `ui-tui/src/domain/liveTurnCost.ts`, `ui-tui/src/components/appChrome.tsx`; toggle `/cost`; audit `windows/audits/RUN_STATUS_BAR_COST_E2E.bat`. **Na TUI-wijzigingen:** `windows/REBUILD_TUI.bat` + Hermes **volledig** herstarten (draaiende sessie laadt geen nieuwe `dist/entry.js`). Klassieke CLI: eindpaneel via `ChatConsole(theme=get_assistant_console_theme())`; tijdens stream (met `streaming=false`) ruwe markdown, Rich pas op het eindpaneel.

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
| `audits\RUN_STATUS_BAR_COST_E2E.bat` | Statusbalk-kosten E2E (rich, 10 stappen) |
| `audits\RUN_STATUS_BAR_COST_E2E.bat -ApplyDisplayFix` | Zelfde + display sync vóór audit |
| `audits\RUN_AUDITS.bat -IncludeStatusBarCostE2E` | Statusbalk E2E in gecombineerde poort |
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

## Wat de fork al doet

- `launch_hermes.bat`: detecteert `WT_SESSION`; zonder WT → `wt -M` + herstart; **geen** tweede maximize in `ComSpec` als je al in WT zit.
- `run_hermes.ps1`: zet `COLORTERM=truecolor` in WT; activeert VT via `enable_console_ansi.ps1`.
- `start_hermes_split.bat`: split-pane logs in WT.

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
