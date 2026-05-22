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
```

of: `hermes config set display.skin default` — daarna Hermes opnieuw starten.

### Markdown in antwoordpanelen (### koppen, **vet:**)

Met `display.final_response_markdown: render` gebruikt Rich standaard **magenta** koppen — geen skin-bug.
De fork past sinds de skin-markdown-theme in `cli.py` (`_skin_markdown_theme`) goud/amber aan op de actieve skin (`banner_title`, `ui_label`, …).

### API-keys (twee Hermes-homes)

Als `HERMES_HOME=%LOCALAPPDATA%\hermes` maar keys alleen in `%USERPROFILE%\.hermes\.env` staan → Gemini **HTTP 400 invalid API key**.

```bat
windows\SYNC_HERMES_API_ENV.bat
```

Kopieert o.a. `GOOGLE_API_KEY` van `%USERPROFILE%\.hermes\.env` naar `%LOCALAPPDATA%\hermes\.env` (root, niet `profiles\<naam>`).

| Script | Doel |
| ------ | ---- |
| `APPLY_TEAM_DISPLAY.bat` | `skin=default`, `final_response_markdown=render`, `streaming=false`, `compact=true` op **root** config |
| `SYNC_HERMES_API_ENV.bat` | API-keys naar actieve root `.env` |

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
