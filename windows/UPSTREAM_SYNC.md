# Upstream-sync: NousResearch + jouw fork (Windows NL)

## Waarom dit bestand bestaat

- **`hermes update`** haalt code van **`origin`** (meestal jouw fork op GitHub).
- **NousResearch/hermes-agent** levert officiële fixes en features via de remote **`upstream`**.
- Een **fork is geen blokkade** — je mist updates alleen als je **niet** periodiek upstream in je fork merge.

**Eén werkende checkout:** `windows\launch_hermes.bat` → repo-root met `origin` = fork en `upstream` = Nous.

**Niet mengen** met `%LOCALAPPDATA%\hermes\hermes-agent` als die `origin` = NousResearch heeft (andere tree). Diagnose: `windows\scripts\which_hermes_repo.ps1`.

---

## Remotes controleren (eenmalig)

Vanuit je dev-repo (map met `cli.py`):

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
git remote -v
```

Verwacht:

| Remote | URL |
| ------ | --- |
| `origin` | `https://github.com/J80-droid/hermes-agent-windows-nl.git` |
| `upstream` | `https://github.com/NousResearch/hermes-agent.git` |

Ontbreekt `upstream`:

```cmd
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch upstream
```

---

## Taakbalk-icoon na update

Na een geslaagde update draait de keten **`fix_hermes_taskbar_pins.ps1`** (regenereert 7-lagen `.ico` uit `assets/Hermes_logo.png`, bouwt `windows\*.lnk` opnieuw, werkt pins bij). Blijft een pin of Verkenner-icoon fout (wit document, generiek H)?

1. **`python windows/tools/generate_colored_hermes_icons.py`** (als PNG/bron ontbrak: ook `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`)
2. **`FIX_TASKBAR_ICONS.bat`** → **F5** in `windows\`
3. **Losmaken** van de oude pin (niet `.bat` slepen)
4. **`windows\Hermes - update - naar taakbalk slepen.lnk`** (of andere rol) → **Vastmaken aan taakbalk**

Kleuren: goud = start/RAG, groen = setup, wit = update, roze = backup, cyaan = restore.

Taakbalk-.lnk: update = `hermes_logo_update.ico` (wit/zilver). Gebruik **niet** `hermes_taskbar_white.ico` in `.lnk` (oude H-stub in Explorer).

**Git dirty na update:** icoon-generator kan `assets/Hermes_logo.png` en `windows/hermes_logo.ico` wijzigen. Dat is normaal — `git restore` die bestanden of doe een branding-commit; preflight laat alleen branding door.

## Standaard sync: `windows\UPDATE_HERMES.bat` of `hermes_update.bat`

**Eén commando** — preflight zit **in** `upstream_sync.ps1` (`-Phase Update`, default):

```cmd
windows\UPDATE_HERMES.bat
```

| Stap | In script? |
| ---- | ---------- |
| Schone `git status` + `git fetch upstream` + ahead/behind | Ja (preflight) |
| Waarschuwing bij achterstand >20 + J/N | Ja |
| `hermes update` (merge upstream + deps) | Ja |
| RAG `[rag]` + script-keten verify | Ja (post-merge, via `verify_windows_script_chain.ps1` — **geen** pause) |
| Merge-conflicten oplossen | **Nee** (handmatig) |
| Waarschuwing tegen `git reset --hard` | Ja (banner bij Update) |
| `git push` / `--mcp-test` | Optioneel (flags hieronder) |

Optionele flags (doorgeven aan `.bat` of ps1):

```cmd
powershell -File windows\upstream_sync.ps1 -Phase Update -McpTest -Push
```

**Verify in de UPDATE-keten:** `upstream_sync.ps1` roept `verify_windows_script_chain.ps1` aan (niet `VERIFY_WINDOWS_CHAIN.bat`). De `.bat` eindigt met `pause` voor handmatig gebruik; in de keten zou dat de flow blokkeren tot je een toets indrukt.

**Grijze uitleg in het venster:** bij preflight (ahead/behind), vóór `[j/N]`, en per fase (1/3–3/3).

Alleen status (geen update):

```cmd
powershell -File windows\upstream_sync.ps1 -Phase Preflight
```

`hermes_update.bat` = dezelfde keten als `UPDATE_HERMES.bat` (niet meer alleen `launch_hermes update` zonder preflight).

`hermes update` (CLI) met **`HERMES_UPDATE_FROM_UPSTREAM=1`** doet alleen git merge + deps — preflight/post-merge alleen via bovenstaande bats. Dat doet:

1. **`git fetch upstream`** + **`git merge upstream/main`** (NousResearch — niet alleen fork `origin`)
2. Python-afhankelijkheden opnieuw installeren (zoals `hermes update` altijd deed)

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
windows\hermes_update.bat
```

Bij merge-conflicten: los ze op, commit, run het batchbestand opnieuw.

**Nieuwe Hermes-sessie** starten na grote updates.

### Handmatige merge (zelfde als het batchbestand stap 1)

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
git fetch upstream
git merge upstream/main
git push origin main
```

Daarna optioneel nog `windows\hermes_update.bat` voor deps.

---

## Alternatief: GitHub “Sync fork”

1. Open je fork op GitHub → **Sync fork** (of vergelijkbaar).
2. Lokaal:

   ```cmd
   cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
   git pull origin main
   windows\hermes_update.bat
   ```

---

## Wat `hermes update` wél / niet doet

| Situatie | Gedrag |
| -------- | ------ |
| **`windows\UPDATE_HERMES.bat`** / **`hermes_update.bat`** | Zelfde keten: preflight + upstream merge + RAG-postinstall |
| **`hermes update` zonder env-var** | Nog steeds **`origin`** (fork) — zoals upstream Hermes |
| Eigen RAG-commits | Blijven behouden via **merge** (niet `reset --hard` op upstream) |
| Conflicten bij merge | Update stopt — handmatig oplossen (`UPSTREAM_SYNC.md` conflict-tabel) |

---

## Conflicten: waar je ze verwacht

Bij merge van Nous in jouw fork botsen vaak **jouw fork-only** paden met upstream-wijzigingen.

### Hoge prioriteit (RAG — meestal **jouw versie behouden**)

| Pad | Richtlijn |
| --- | --------- |
| `scripts/rag_pipeline/**` | **Behoud fork** (ingest, MCP, ACTIVATION, RAG-tests) |
| `windows/scripts/update_knowledge.bat` | **Behoud fork** |
| `windows/scripts/install_rag_extras.ps1` | **Behoud fork** |
| `windows/scripts/register_lancedb_mcp.ps1` | **Behoud fork** |
| `scripts/rag_pipeline/register_mcp_config.py` | **Behoud fork** |
| `agent/prompt_builder.py` (citatie `LANCEDB_RAG_*`) | **Behoud fork** of handmatig samenvoegen |
| `cli.py` / `web/src/lib/ragCitations.ts` (bron-chips) | **Behoud fork** |
| `pyproject.toml` extra `[rag]` | **Behoud fork**; neem upstream pins over voor **core** deps waar geen RAG-conflict is |
| `memory-bank/**`, `windows/UPSTREAM_SYNC.md`, `windows/INSTITUTIONAL.md` | **Behoud fork** |

### Meestal upstream overnemen (tenzij bewust aangepast)

| Pad | Richtlijn |
| --- | --------- |
| `hermes_cli/main.py` (grote upstream fixes) | Meestal **theirs** / upstream, daarna RAG-hooks opnieuw checken |
| `gateway/**`, `tools/**` | Vaak **upstream**; test messaging na merge |
| `tests/**` (niet onder `tests/rag_pipeline/`) | Vaak **upstream** |
| `uv.lock` | Na merge: `uv lock` of volg upstream lock; daarna `pip install -e ".[rag]"` |

### `pyproject.toml` / `uv.lock` speciaal

- Extra **`[rag]`** hoort in de fork; combineer **niet** blind `[all,rag]` (youtube/markitdown-conflict).
- Na merge:

  ```cmd
  pip install -e ".[rag]"
  pip install "markitdown[all]==0.1.5"
  ```

  Of: `windows\scripts\install_rag_extras.ps1`

---

## Upstream-wijzigingen na merge (inspectie)

**Niet** elke Nous-commit handmatig in dit bestand kopiëren — dat veroudert. Gebruik **git** (of GitHub compare) als bron.

### Wat is er binnengekomen?

Direct na `windows\UPDATE_HERMES.bat` (of na `git merge upstream/main`):

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
git fetch upstream
git log --oneline -15 upstream/main
```

Alleen de commits van de **laatste merge** (na merge-commit op `main`):

```cmd
git log --oneline -20 --first-parent
```

Of: op GitHub → fork → **Compare** `upstream/main` met je branch vóór de merge.

### Rooktest — wat raakt deze fork?

| Gebied | Altijd testen na merge | Alleen als je het gebruikt |
| ------ | ---------------------- | --------------------------- |
| RAG ingest / MCP / `search_knowledge` | Ja | — |
| Klassieke CLI (`start_hermes.bat`), display/skin, markdown, SOUL-sync | Ja | — |
| `VERIFY_WINDOWS_CHAIN.bat` / taakbalk-iconen | Ja (zit in UPDATE-keten) | — |
| Computer-use / browser-automation | — | Ja |
| SSH / remote sync | — | Ja |
| Ink-TUI / Termux | — | Ja |

**Tip:** commit-titels met `fix(tui)`, `fix(computer-use)`, `fix(ssh)` → kolom “alleen als je het gebruikt”. `scripts/rag_pipeline`, `windows/` → meestal **jouw fork**; bij conflicten fork behouden (zie conflict-tabel hieronder).

### Optioneel: korte merge-notitie (max. 5 regels)

Alleen na **grote** merges (B > 20 of conflict-oplossing). Vrij formaat in je eigen log (`%USERPROFILE%\data\RECOVERY.md` of team-kanaal):

```text
2026-05-22 — merge upstream/main (B=10): TUI scrollback + computer-use AX-cap. Getest: legal MCP, start_hermes, display default.
```

Geen verplichting; git history blijft de volledige changelog.

---

## Na elke upstream-merge (checklist)

1. `git status` — geen onopgeloste conflicten.
2. **Inspectie:** `git log --oneline -15 upstream/main` (zie sectie hierboven).
3. `pytest tests/rag_pipeline/ -q -m "not rag_integration"`
4. `windows\scripts\install_rag_extras.ps1` (MCP + deps)
5. `windows\scripts\which_hermes_repo.ps1` — `lancedb-knowledge: JA`
6. `VERIFY_WINDOWS_CHAIN.bat` (of vertrouw op UPDATE-keten).
7. Nieuwe Hermes-sessie; rooktest: `search_knowledge` (zie `scripts/rag_pipeline/ACTIVATION.md`)
8. Display/API-home: `APPLY_TEAM_DISPLAY.bat`, `SYNC_HERMES_API_ENV.bat`, `SYNC_SOUL_SNIPPETS.bat` (zie `TERMINAL_WINDOWS.md`, `docs/INSTITUTIONAL_PRESENTATION.md`)
9. Institutioneel E2E: `windows\audits\RUN_INSTITUTIONAL_E2E.bat` (**11 stappen**: SOUL, display alle profielen incl. `assistant_*`, Rich-renderer 2e, profielwissel 9–11)
10. Rooktest presentatie (subset): `pytest tests/cli/test_institutional_rich_render.py tests/cli/test_skin_markdown_theme.py tests/agent/test_rich_output.py -q`

---

## Snelle status

```cmd
git fetch upstream
git rev-list --left-right --count HEAD...upstream/main
```

Uitvoer `A  B` (twee getallen, gescheiden door spatie):

- **A** = commits op jouw branch die upstream niet heeft (jouw fork-werk).
- **B** = commits op upstream die jij nog niet hebt (**achterstand op Nous**).

Grote **B** → plan een merge.

---

## Voorkomen van zware conflicten (routine)

Je fork **deelt** de codebase met Nous; RAG/Windows blijft **jouw** laag. Conflicten ontstaan vooral als je **maanden** niet merge’t en Nous intussen `pyproject.toml`, `run_tests.sh` of `uv.lock` wijzigt.

### 1. Vaak klein mergen (belangrijkste regel)

| Frequentie | Actie |
| -------- | ----- |
| **Wekelijks** (of na elke Nous-release) | `windows\hermes_update.bat` |
| **Vóór grote eigen wijzigingen** | Eerst upstream binnenhalen, dan RAG/features bouwen |
| **B > 20** (zie “Snelle status”) | Merge plannen — niet wachten tot 70+ commits |

Kleine merges: vaak **geen** conflicten of alleen `uv.lock`. Grote merges: vrijwel altijd 2–4 bestanden.

### 2. Vaste “fork-zone” — niet wijzigen tenzij nodig

Houd RAG en Windows **in bekende paden** (zie conflict-tabel hierboven). Wijzig **niet** in upstream-kern tenzij bewust:

- `hermes_cli/main.py`, `gateway/**` → liever upstream volgen
- `scripts/run_tests.sh` / test-infra → volg Nous; fork alleen `tests/rag_pipeline/` + pytest-markers in `pyproject.toml`

Nieuwe fork-logica: liever **nieuwe bestanden** (`scripts/rag_pipeline/*`, `windows/scripts/*`) dan grote edits midden in upstream-bestanden.

### 3. Vóór `hermes update`: 30 seconden check

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
git status
git fetch upstream
git rev-list --left-right --count HEAD...upstream/main
```

- **`git status` niet schoon** → commit of stash. **Uitzondering:** alleen `assets/Hermes_logo.png` en `windows/hermes*.ico` (na icoon-generator) — `UPDATE_HERMES.bat` gaat door met waarschuwing.
- **Grote B** → reken op conflicten; lees conflict-tabel (pyproject, run_tests, uv.lock).

### 4. Na elke geslaagde merge

1. `git push origin main` (fork op GitHub = origin voor `hermes update`)
2. `pip install -e ".[rag]"` of `windows\scripts\install_rag_extras.ps1`
3. Rooktest legal/core MCP (`update_knowledge.bat --mcp-test`)
4. Nieuwe Hermes-sessie

### 5. Wat je niet moet doen

| Niet doen | Waarom |
| --------- | ------ |
| `git reset --hard upstream/main` | Wist RAG-fork, MCP-sync, docs NL |
| Alleen GitHub “Sync fork” zonder lokale test | OK als daarna lokaal `git pull` + RAG-check |
| Maanden alleen `hermes update` zonder te committen/pushen | Lokale en remote fork lopen uiteen |
| Conflicten in `scripts/rag_pipeline/**` blind “theirs” kiezen | Verliest ingest/MCP |

Bij `UPDATE_HERMES.bat` / `-Phase Update`: vaste **banner** tegen `reset --hard` (geen detectie achteraf). Overslaan: `HERMES_SKIP_RESET_WARNING=1` of `windows\SKIP_HARD_RESET_WARNING`.

### 6. Optioneel: merge-driver voor lockfile (gevorderd)

Bij herhaaldelijk `uv.lock`-conflict na merge:

```cmd
git checkout --theirs uv.lock
uv lock
git add uv.lock
```

Daarna RAG-deps opnieuw: `pip install -e ".[rag]"`.

---

## Troubleshooting UPDATE

| Symptoom | Oorzaak | Oplossing |
| -------- | ------- | --------- |
| `NativeCommandError` op `Using Python ... environment at:` | PowerShell 5.1 + `2>&1` op **conda** — stderr wordt fout | Gebruik `HermesNativeInvoke.ps1` (`Invoke-HermesNativeCommand`); geen `2>&1 \| Out-Host` op conda in fork-scripts |
| `[ERROR] hermes update eindigde met code No Hermes processes...` | stdout van `hermes update` als “exitcode” gelezen | Zelfde: native invoke retourneert alleen `[int]$LASTEXITCODE` |
| `Werkmap niet schoon` | Uncommitted wijzigingen | Commit/stash; **alleen** `assets/Hermes_logo.png` + `windows/hermes*.ico` mag door preflight |
| Keten stopt code 1, geen merge-conflict | Zie regels hierboven; daarna `UPDATE_HERMES.bat` opnieuw | |

Canonieke wrapper: `windows/HermesNativeInvoke.ps1` — gebruikt door `upstream_sync.ps1` voor `hermes update`.

---

## Gerelateerd

- `windows/INSTITUTIONAL.md` — Windows + één checkout
- `scripts/rag_pipeline/ACTIVATION.md` — RAG ingest/MCP/rooktest
- `memory-bank/progress.md` — operationele voortgang
