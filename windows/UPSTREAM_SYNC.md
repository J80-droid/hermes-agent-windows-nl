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

**Optioneel — codebase smoke na post-merge** (E1/E2, geen E3):

```cmd
windows\UPDATE_HERMES.bat -IncludeCodebaseSmoke
windows\UPDATE_HERMES.bat -IncludeCodebaseSmokeE2E
```

Na gewone `git pull`: `windows\POST_GIT_PULL.bat -IncludeCodebaseSmoke` (~32s) of `-IncludeCodebaseSmokeE2E` (~45s, E2E-poort). Runner: `windows\scripts\Invoke-PostSyncCodebaseSmoke.ps1`. Zie `docs/CODEBASE_AUDIT_EVIDENCE.md`.

### Merge mislukt (conflicten)? Gebruik `MERGE_UPSTREAM.bat`

`hermes update` doet **`git merge --abort`** bij conflicten — je ziet geen conflict-markers.

**Aanbevolen (IDE-guided, geen blind merge):**

```cmd
windows\MERGE_UPSTREAM.bat -PromptOnly
```

Voorspelt conflicten via `git merge-tree` — **geen git-wijziging**. Schrijft een markdown-prompt naar `%LOCALAPPDATA%\hermes\merge_prompts\` die je in Cursor plakt. Per conflictbestand bevat de prompt een **git-diff snippet** (`HEAD` vs `upstream/main`) zodat de IDE inhoud ziet vóór de merge — ook zonder `<<<<<<<` markers op schijf.

**Echte merge + prompt:**

```cmd
windows\MERGE_UPSTREAM.bat
```

Start merge, genereert IDE-prompt voor open conflicten, **geen** blind `checkout --ours/theirs` (tenzij `-AutoResolve`).

**Na IDE-fix:**

```cmd
git add .
windows\MERGE_UPSTREAM.bat -FinalizeOnly
```

| Stap | Script |
| ---- | ------ |
| 0 (optioneel) | `-PromptOnly` — preview + prompt, geen merge |
| 1 | `git merge upstream/main` (conflicten blijven open) |
| 2 | IDE-prompt met per-bestand richtlijn + conflict-snippet |
| 3 | Cursor lost semantisch op (`pyproject.toml`, `prompt_builder.py`, …) |
| 4 | `-FinalizeOnly` → merge-commit + `UPDATE_HERMES.bat` |

**Power users (blind auto-resolve, oude gedrag):**

```cmd
windows\MERGE_UPSTREAM.bat -AutoResolve
```

**Flags:** `-PromptOnly`, `-NoPrompt`, `-AutoResolve`, `-FinalizeOnly`, `-LockTheirs`, `-SkipContinueUpdate`, `-PromptOut <pad>`.

| Stap | In script? |
| ---- | ---------- |
| Schone `git status` + `git fetch upstream` + ahead/behind | Ja (preflight) |
| Waarschuwing bij achterstand >20 + J/N | Ja |
| `hermes update` (merge upstream + deps) | Ja |
| Trust runtime (`SYNC_TRUST_RUNTIME.bat`, geen scrub + USER-regel snapshot) | Ja (post-merge, `HERMES_SKIP_PAUSE=1`). Bij FAIL: `pending_trust_runtime.json`; eerste `start_hermes.bat` herstelt via lichte trust-nazorg |
| API + vault-env (`sync_hermes_api_env.ps1` via trust/UPDATE/POST_GIT_PULL) | Ja (`OBSIDIAN_VAULT_PATH` naar alle profiel-`.env`) |
| Hermes home + config drift (`verify_hermes_home`, `verify_hermes_config_drift`) | Ja (post-merge; bij FAIL: `APPLY_HERMES_HOME_MIGRATION.bat`) |
| Domein-toolsets (`SYNC_DOMAIN_TOOLSETS.bat`) | Ja (post-merge, na trust runtime) |
| SOUL anatomy deploy (`launch_soul_anatomy_deploy.ps1 -Force -Quiet`) | Ja (post-merge: 13 templates + stamp) |
| Institutioneel runtime (`apply_institutional_runtime.ps1 -SkipE2E -NoPause -SkipSoul`) | Ja (post-merge: display; snippets overgeslagen na soul deploy) |
| RAG `[rag]` + script-keten verify | Ja (post-merge, via `verify_windows_script_chain.ps1` — **geen** pause) |
| Merge-conflicten oplossen | **Nee** (handmatig) |
| Waarschuwing tegen `git reset --hard` | Ja (banner bij Update) |
| `git push` / `--mcp-test` | Optioneel (flags hieronder) |

Optionele flags (doorgeven aan `.bat` of ps1):

```cmd
powershell -File windows\upstream_sync.ps1 -Phase Update -McpTest -Push
```

**Verify in de UPDATE-keten:** `upstream_sync.ps1` vernieuwt eerst taakbalk-.lnk (`fix_hermes_taskbar_pins.ps1`), daarna `verify_windows_script_chain.ps1` (niet `VERIFY_WINDOWS_CHAIN.bat`). Bij handmatige verify: auto-repair via dezelfde fix als `.lnk` afwijkt. De `.bat` eindigt met `pause` voor handmatig gebruik; in de keten zou dat de flow blokkeren tot je een toets indrukt.

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

### TUI statusbalk kosten (rich cost bar)

| Pad | Actie na merge |
| --- | -------------- |
| `hermes_cli/usage_snapshot.py` | **Behoud fork** — breakdown + usage payload |
| `tui_gateway/server.py` | `_get_usage` → delegatie naar `build_session_usage_snapshot` |
| `ui-tui/src/domain/usageCostBar.ts` | **Behoud fork** — responsive formatter + `statusRuleColumns` + `resolveStatusRuleLayout` (optionele `cwdReserve` van `statusRuleWidths`) |
| `ui-tui/src/components/appChrome.tsx` | **Combineer:** upstream `statusRuleWidths` + fork cost inline; `cwdReserve: rightWidth + separatorWidth` |
| `hermes_cli/profiles.py` | **Combineer:** `strip_model_block_from_profile_config` vóór `_maybe_register_gateway_service` (s6 container) |
| `ui-tui/src/app/createGatewayEventHandler.ts` | turn/tool client-side hooks + live `~NK tok` fallback |
| `hermes_cli/config.py` | **Behoud fork** — `show_cost: true`, `cost_bar_mode: rich` defaults |
| `agent/usage_pricing.py` | **Geen fork-wijzigingen** — snapshot volgt upstream API |
| `windows/team_display.defaults` | `show_cost=true`, `cost_bar_mode=rich` |

### Classic CLI parity (statusbalk kosten)

| Pad | Actie na merge |
| --- | -------------- |
| `hermes_cli/status_bar_cost.py` | **Behoud fork** — Python formatter (mirror `usageCostBar.ts`) |
| `tests/hermes_cli/test_status_bar_cost.py` | **Behoud fork** — unit tests formatter |
| `cli.py` | **Behoud fork** (al in keepOurs) — dunne hooks: `_show_cost`, `_append_status_bar_cost_fragments`, `/cost` |
| `hermes_cli/commands.py` | `CommandDef("cost", …)` na merge handmatig behouden indien upstream ontbreekt |

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
7. **Split-home drift:** `VERIFY_HERMES_CONFIG_DRIFT.bat` — bij FAIL eenmalig `APPLY_HERMES_HOME_MIGRATION.bat` (zie `docs/HERMES_HOME_WINDOWS.md`).
8. Nieuwe Hermes-sessie; rooktest: `search_knowledge` (zie `scripts/rag_pipeline/ACTIVATION.md`)
9. SOUL/display: **automatisch** in `UPDATE_HERMES.bat` post-merge (`launch_soul_anatomy_deploy -Force`, daarna `apply_institutional_runtime -SkipSoul`). Handmatig: `APPLY_SOUL_ANATOMY_RUNTIME.bat` of `APPLY_INSTITUTIONAL_RUNTIME.bat`
10. SOUL startketen E2E: `windows\audits\RUN_SOUL_DEPLOY_START_E2E.bat`
11. Institutioneel E2E: `windows\audits\RUN_INSTITUTIONAL_E2E.bat` (**11 stappen**)
12. Rooktest presentatie: `pytest tests/cli/test_institutional_rich_render.py … -q`

**Laatste volledige audit:** `windows/audits/UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md` (merge 58 commits + UPDATE + E2E PASS). Na merge 87 commits (2026-05-25): `windows\audits\RUN_UPSTREAM_MERGE_INTEGRATION_E2E.bat` (10/10: vitest statusRule/usageCostBar, pytest profile+s6, harness).

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
