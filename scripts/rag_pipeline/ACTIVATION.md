# LanceDB RAG-pijplijn activeren (handmatige terminalworkflow)

Dit document is de **in-repo** kopie van het activatieplan (Cursor-plan: *LanceDB RAG activeren*). Houd het hier bij voor versiebeheer; werk het bij wanneer de workflow wijzigt.

## Context

Scripts in deze map:

- `ingest.py` — orchestratie: scan, chunking, upsert, voortgang.
- `source_formats.py` — centrale extensiematrix (plain / MarkItDown / media).
- `ingest_config.py` — uitsluitingen (`node_modules`, `~$*`, binaries); optioneel **`HERMES_RAG_MAX_FILE_MB`** (standaard **geen** limiet).
- `ingest_handlers.py` — MarkItDown + optionele **pandoc**-fallback voor legacy Office/OpenDocument.
- `ingest_state.py` — incrementele ingest (`mtime`/`size`/content-fingerprint) in `HERMES_LANCEDB_PATH/.hermes_rag_ingest_state.json`.
- `orphan_cleanup.py` — verwijdert oude chunk-`id`s na inkrimpen of verwijderen van een bron.
- `subtitle_sidecar.py` — `.vtt`/`.srt` vóór Whisper; geen dubbele index naast media.
- `audio_transcriber.py` — lokale audio/video via faster-whisper + ffmpeg.
- `mcp_server.py` — stdio MCP-server met tool `search_knowledge`.
- `kb_schema.py` — gedeeld `KnowledgeSchema` (velden **`id`**, `text`, `vector`, `source`), padconstanten en `list_all_table_names()` (LanceDB `list_tables()` API).

**Idempotente upsert:** elke chunk krijgt een vaste **`id`** = SHA-256 van `(<relatief pad>\\0#<chunk-index>)`. **`merge_insert(..., on='id')`** werkt bestaande rijen bij. **Orphan cleanup** (standaard aan) verwijdert chunk-`id`s die niet meer in de nieuwste chunk-set van die bron zitten. **Incrementele ingest** (standaard aan) slaat ongewijzigde bronnen over via ingest-staat naast LanceDB.

### Omgevingsvariabelen (institutioneel)

| Variabele | Default | Betekenis |
| --------- | ------- | --------- |
| `HERMES_RAG_INCREMENTAL` | `1` | Alleen gewijzigde bronnen opnieuw indexeren |
| `HERMES_RAG_FORCE_FULL` | `0` | `1` = volledige scan (negeert incrementeel) |
| `HERMES_RAG_ORPHAN_CLEANUP` | `1` | Oude chunks per bron verwijderen na upsert |
| `HERMES_RAG_MAX_FILE_MB` | *(niet gezet)* | Geen limiet — **alle** bronnen. Zet bijv. `150` om bestanden boven 150 MB over te slaan |
| `HERMES_RAG_HASH_FULL_MAX_MB` | `32` | Volledige SHA-256 onder deze grootte; daarboven fingerprint |
| `HERMES_WHISPER_MODEL` | `medium` | faster-whisper model (kwaliteit; `large-v3` trager/nauwkeuriger) |
| `HERMES_RAG_PREFER_SIDECAR` | `0` | `1` = gebruik `.vtt`/`.srt` i.p.v. Whisper (sneller, niet standaard) |
| `HERMES_RAG_PERF_PROFILE` | `balanced` | Preset vóór ingest: `safe`, `balanced`, `fast`, `off` — zie `windows/scripts/rag_ingest_perf_defaults.ps1` |
| `HERMES_RAG_CONVERT_WORKERS` | `1` (ingest.py); `balanced` zet CPU-afhankelijk (2–8) | Parallel MarkItDown per golf; cap in ingest: `min(cpu, 8)` |
| `HERMES_RAG_EMBED_BATCH` | `64` | Embedding-batchgrootte; cap in ingest: `512` |
| `HERMES_RAG_CONVERT_HEARTBEAT_SEC` | `3.0` | Heartbeat tijdens parallelle conversie; `0` = uit |
| `HERMES_RAG_VERBOSE` | `0` | `1` = uitgebreide regels per bestand; `0` = compact (balk + ✓/WARN) |

**UI:** `ingest.py` toont een gouden voortgangsbalk `n/totaal` (zoals `install-jamel.ps1`). In een interactieve terminal; bij redirect naar log blijven tekstregels zichtbaar.

**Performance:** `update_knowledge.bat` roept `rag_ingest_perf_defaults.ps1` aan na conda-activate. Expliciet gezette env-variabelen worden **niet** overschreven. Taakplanner: `set HERMES_RAG_PERF_PROFILE=safe` of `set HERMES_NONINTERACTIVE=1` + `HERMES_RAG_FRESH=1`.

**Schema-upgrade:** bestond `knowledge_base` al **zonder** kolom `id`, dan stopt `ingest.py` met een foutmelding — eenmalig database wissen (**J** / `HERMES_RAG_FRESH=1`) of map handmatig verwijderen, daarna opnieuw indexeren.

**Paden:** `~/data/...` wordt op Windows `%USERPROFILE%\data\...` (niet automatisch je repo-schijf). Optioneel (institutioneel): zet **`HERMES_RAG_RAW_SOURCE`** en **`HERMES_LANCEDB_PATH`** (absolute paden of `~` / `%VAR%`) — zelfde variabelen lezen `ingest.py` en `kb_schema.py`; `windows\scripts\update_knowledge.bat` zet `HERMES_LANCEDB_PATH` vóór `python` gelijk aan de map die bij **J** wordt gewist.

**MCP-server:** start zonder crash ook als de database nog leeg is: ontbreekt `knowledge_base`, dan wordt een **lege** tabel met `KnowledgeSchema` aangemaakt. Voor echte antwoorden moet je daarna alsnog `ingest.py` draaien.

```mermaid
flowchart LR
  deps[Pip dependencies]
  data[Raw files in user data dir]
  ingest[ingest.py]
  mcp[hermes mcp add]
  deps --> ingest
  data --> ingest
  ingest --> mcp
```

## 100%-checklist (code vs. jouw run)

| # | Onderdeel | In repo (code) | Jouw run (verplicht voor E2E) |
| - | --------- | -------------- | ----------------------------- |
| 1 | CLI/Web bron-chips (`cli.py`, `web/…/Markdown.tsx`) | Ja — `[Bron: …]` → backticks | — |
| 2 | `pyproject.toml` extra `[rag]` | Ja — `pip install -e ".[rag]"` | Eenmalig in `hermes-env` |
| 3 | Automatische MCP + RAG-deps | Ja — `install-jamel.ps1` / `setup_hermes_windows.ps1` → `install_rag_extras.ps1` | Nieuwe sessie na install |
| 4 | `tests/rag_pipeline/` (pytest) | Ja | `pytest tests/rag_pipeline/ -q` |
| 5 | Rooktest (5 commando’s) | Ja — hieronder | Alle 5 stappen doorlopen |
| A | `update_knowledge.bat` tot einde | — | Log: `[OK] Ingestie-scan afgerond` |
| B | MCP + nieuwe Hermes-sessie | Script registreert MCP | `hermes mcp test lancedb-knowledge` OK |
| C | `search_knowledge` op bekende zin | — | Antwoord met `[Bron: …]` uit index |

Zonder **A+B+C** is de keten nooit 100% operationeel — ook niet met perfecte code.

## Institutioneel (P3 — mitigaties in repo)

| Risico | Mitigatie |
| ------ | --------- |
| conda vs. uv `.venv` | `install_rag_extras.ps1` → `pip install -e ".[rag]"` op **beide** (`rag_python_resolve.ps1`) |
| MCP relatief pad / verkeerde cwd | `register_mcp_config.py` — **absoluut** pad naar `mcp_server.py` + env `HERMES_REPO_ROOT`, `HERMES_LANCEDB_PATH` |
| Whisper/ffmpeg | `[rag]` bevat `faster-whisper`; **ffmpeg** moet op PATH (winget/choco) |
| Oud schema zonder `id` | `python scripts/rag_pipeline/schema_migrate.py` (inspect / `--backup-and-reset`) |
| Taakplanner wacht op J/N | `set HERMES_NONINTERACTIVE=1` of `HERMES_RAG_FRESH=0` vóór `update_knowledge.bat` |
| LanceDB-lock bij wissen | Waarschuwing in batch; sluit Hermes + MCP |
| Dev-repo vs. install-clone | `install_rag_extras.ps1` toont beide paden; werk in de checkout die je start |
| CI regressie | GitHub job `rag`: unit tests + `rag_integration` + `web/scripts/test-rag-citations.mjs` |
| `uv lock` met `[all,rag]` | **Niet combineerbaar** — `[rag]` gebruikt `markitdown==0.1.5`; daarna apart `pip install "markitdown[all]"`. `uv lock` voor `[dev,rag]` werkt wel (zie `uv.lock`). |
| Twee config-paden | Hermes kan `~/.hermes/config.yaml` **of** `%LOCALAPPDATA%\hermes\config.yaml` gebruiken — `which_hermes_repo.ps1` |
| Klikbare bron (P4) | `HERMES_RAG_BRON_FILE_LINKS=1` + `HERMES_RAG_RAW_SOURCE` → `[Bron: naam](file:///...)` |
| Watch-folder (P4) | `windows\scripts\watch_rag_sources.ps1` (debounce → `update_knowledge.bat`) |
| Gateway/Telegram chips | Web-dashboard: `Markdown.tsx`; messaging-platforms: nog geen bron-chips |

## Rooktest (5 commando’s, vanuit repo-root, conda `hermes-env`)

Alle commando’s in **één** geactiveerde shell; `cd` eerst naar de Hermes-repo-root (waar `scripts/` relatief klopt).

1. **Dependencies (eenmalig of na upgrade):**

   ```text
   pip install -e ".[rag]"
   ```

   Alternatief handmatig: `pip install lancedb sentence-transformers "markitdown[all]"` + `pip install mcp` (of `hermes-agent[mcp]`).

2. **Index bijwerken** (laat tot `[OK]` / einde lopen; bij grote media kan dit uren duren):

   ```text
   windows\scripts\update_knowledge.bat
   ```

   Of: `python scripts/rag_pipeline/ingest.py` met dezelfde env-variabelen als het batchbestand.

3. **MCP registreren** (eenmalig; Windows met volledig python-pad):

   ```text
   powershell -ExecutionPolicy Bypass -File windows\scripts\register_lancedb_mcp.ps1
   ```

   Handmatig equivalent: zie stap 5 hieronder.

4. **MCP controleren:**

   ```text
   hermes mcp list
   hermes mcp test lancedb-knowledge
   ```

5. **Nieuwe Hermes-sessie + gerichte tool-vraag** (split-venster of `hermes` CLI):

   ```text
   Voer search_knowledge uit op de query 'VWO Elite' en citeer met [Bron: bestandsnaam].
   ```

   Verwachting: antwoord uit **lokale** index (rookbestand `test.txt` of jouw bronnen), niet een willekeurige marketingpagina van het web.

## Workflowtip: smoke-test

1. Map: `~/data/raw_source_files` (bijv. op Windows `%USERPROFILE%\data\raw_source_files`).
2. Bestand `test.txt` met bijvoorbeeld: *VWO Elite is een geavanceerd platform gebouwd door Jamel. Het lanceert in 2026.*
3. Voer daarna de rooktest hierboven of de stappen hieronder uit.

## Bronbestanden: drie gouden regels

1. **Underscores i.p.v. spaties** in bestandsnamen (`wiskunde_b_…` i.p.v. `Wiskunde B …`) — minder verwarring bij citaten en paden in LLM-output.
2. **Korte, beschrijvende namen** — bijvoorbeeld `wiskunde_b_domein_c_differentiaalrekening.md` i.p.v. `samenvatting1.md`; de bestandsnaam (en pad) wordt als `source`-metadata in LanceDB opgeslagen en helpt vindbaarheid.
3. **Markdown waar mogelijk** — werk theorie bij voorkeur uit in `.md` met duidelijke `##` / `###` koppen; dat sluit aan op de semantische chunking. PDF, Word, PowerPoint, spreadsheets, `.msg` en HTML/XML worden via MarkItDown naar Markdown gezet; opgeschoonde bron-MD blijft ideaal voor maximale structuur.

## Ondersteunde bronbestanden (ingest)

Alles onder `~/data/raw_source_files` wordt per extensie gescand. **Autoritatieve lijst:** [`source_formats.py`](source_formats.py) (`PLAIN_SUFFIXES`, `MARKITDOWN_SUFFIXES`, `AUDIO_SUFFIXES`, `VIDEO_SUFFIXES`).

| Route | Extensies (samenvatting) |
| ----- | ------------------------ |
| **UTF-8 tekst** | `.txt`, `.md`, `.json`, `.jsonl`, `.log`, `.csv`, `.tsv`, `.yaml`, `.yml`, `.toml`, `.ini`, `.rst`, `.adoc`, ondertitels `.vtt`, `.srt`, `.sbv` |
| **MarkItDown → Markdown** | **Office:** `.docx`, `.doc`, `.docm`, `.dotx`, `.dotm`, `.rtf`, `.xlsx`, `.xls`, `.xlsm`, `.xlsb`, `.pptx`, `.ppt`, `.pptm`, `.ppsx`, `.pps`, `.msg`, `.eml` · **OpenDocument:** `.odt`, `.ods`, `.odp` · **Web/PDF:** `.pdf`, `.html`, `.htm`, `.xml`, `.rss`, `.atom` · **Overig:** `.epub`, `.ipynb`, `.zip` · **Beeld:** `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp`, `.tif`, `.tiff`, `.heic` |
| **Whisper + ffmpeg** | **Audio:** `.mp3`, `.m4a`, `.wav`, `.ogg`, `.flac`, `.aac`, `.wma`, `.aiff`, `.opus`, … · **Video:** `.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`, `.wmv`, `.mpeg`, `.3gp`, … |

**Niet geïndexeerd (bewust):** binaries (`.exe`, `.dll`, …), databases (`.sqlite`, `.parquet`), archieven `.7z`/`.rar` (wel `.zip` via MarkItDown), Office-lock `~$*`, mappen `.git` / `node_modules` / `__pycache__`. **Grootte:** standaard geen maximum; optioneel `HERMES_RAG_MAX_FILE_MB=150` (of ander getal) om zeer grote bestanden over te slaan.

Voor **MarkItDown** is `pip install "markitdown[all]"` aanbevolen; voor legacy `.doc`/OpenDocument optioneel **`pandoc`** op PATH (fallback via `ingest_handlers.py`). Voor **media**: standaard **Whisper** (maximale transcriptie-kwaliteit uit de audio). `.vtt`/`.srt` alleen als Whisper ontbreekt/faalt, of expliciet `HERMES_RAG_PREFER_SIDECAR=1` (sneller, kan minder detail hebben). Bij conversiefouten: `[WARN]` en door.

## Windows: snelkoppeling (taakbalk)

Na setup of na **`windows\REFRESH_TASKBAR_SHORTCUTS.bat`** staat in **`hermes-agent\windows\`** o.a. **`Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk`**. Die verwijst naar **`windows\scripts\update_knowledge.bat`** (conda `hermes-env` + `python scripts/rag_pipeline/ingest.py`). Sleep de `.lnk` naar de taakbalk voor één-klik herbouw van de LanceDB-index.

Het batchbestand vraagt eerst **J/N** (tenzij **`HERMES_RAG_FRESH`** gezet is: `1`/`true`/`yes`/`j` = wis, `0`/`n`/`no` = behoud — handig voor taakplanner/CI). **J** verwijdert de LanceDB-map (na rename-check op locks; zie script) — standaard **`%USERPROFILE%\data\my_lancedb`**, of **`HERMES_LANCEDB_PATH`**. **N** laat de map staan; **`ingest.py`** doet dan **upsert** op chunk-`id`, dus geen duplicate chunks voor dezelfde bron+index. Sluit processen die LanceDB openhouden (bijv. MCP `lancedb-knowledge`) voordat je **J** kiest, anders faalt het wissen met een duidelijke fouttekst.

**Conda (geen hardcoded gebruikerspad):** het script zoekt `activate.bat` via **`HERMES_ACTIVATE_BAT`** (volledig pad), **`HERMES_CONDA_ROOT`**, of gangbare locaties onder `%USERPROFILE%` en `%LOCALAPPDATA%`. Omgevingsnaam standaard **`hermes-env`**; override met **`HERMES_CONDA_ENV`**.

## Stappen (eigen terminal, vanuit `hermes-agent` repo-root)

1. **Conda:** activeer `hermes-env` (prompt toont `(hermes-env)`), of bijvoorbeeld  
   `"%USERPROFILE%\miniconda3\Scripts\activate.bat" hermes-env`  
   (of het pad dat bij jullie hoort / `HERMES_CONDA_ROOT` uit `update_knowledge.bat`-logica).

2. **Werkdirectory:** `cd` naar de root van deze repo (waar `scripts/` relatief klopt).

3. **Dependencies:**

   ```text
   pip install -e ".[rag]"
   ```

   (Installeert o.a. `lancedb`, `sentence-transformers`, `markitdown[all]`, `pyarrow` en `mcp` via `pyproject.toml` extra `rag`.)

   **Fail fast:** `ingest.py` importeert `markitdown` statisch bovenaan. Ontbreekt het pakket, faalt het script direct bij start — niet pas na een lange scan.

4. **Ingestie:**

   ```text
   python scripts/rag_pipeline/ingest.py
   ```

5. **Hermes MCP — correcte CLI-syntax** (`--command` = executable, `--args` = script + evt. meer args):

   ```text
   hermes mcp add lancedb-knowledge --command python --args scripts/rag_pipeline/mcp_server.py
   ```

   **Windows:** als `python` op het PATH **niet** dezelfde omgeving is als `hermes-env` (gebruikelijk fout: `ModuleNotFoundError: lancedb`), gebruik het **volledige pad** naar die interpreter, bijvoorbeeld:

   ```text
   hermes mcp add lancedb-knowledge --command %USERPROFILE%\miniconda3\envs\hermes-env\python.exe --args scripts/rag_pipeline/mcp_server.py
   ```

   Start Hermes bij voorkeur vanuit deze repo-root zodat relatieve `--args` kloppen.

6. **Verifiëren:**

   ```text
   hermes mcp list
   hermes mcp test lancedb-knowledge
   ```

   Start daarna een **nieuwe** Hermes-sessie om de tools te laden.

## Koppeling Hermes ↔ `search_knowledge` (waar het spaak loopt)

Als Hermes bij vragen over jouw lokale kennis toch **VWO.com / Google / curl** gebruikt in plaats van LanceDB, ligt dat meestal aan één van deze twee punten:

1. **Geen verse sessie na MCP-wijziging** — Hermes laadt de lijst met MCP-servers en hun tools **alleen bij het starten van een nieuwe sessie**. Een terminalpaneel dat blijft hangen, of Hermes zonder volledige herstart, kent `search_knowledge` dan nog niet.
2. **Te algemene prompt** — Bij zoiets als “Gebruik je knowledge base” kan het model **internet-zoektools** prefereren boven de MCP-tool. Voor een **onomstotelijke rooktest** moet je expliciet naar `search_knowledge` verwijzen.

### Oplossingsmatrix (split commandocentrum, o.a. `start_hermes_split.bat`)

1. **Sessie beëindigen** — In het Hermes-linkerpaneel: `/exit`, of het hele Windows Terminal-venster sluiten (geen “alleen tab sluiten” als je zeker wilt zijn dat het proces weg is).
2. **Opnieuw starten** — Dubbelklik opnieuw op `start_hermes_split.bat` (repo-root). Links start Hermes opnieuw; rechts volgt `Get-Content …\agent.log -Wait -Tail 30` (telemetrie/logstroom).
3. **Rechterpaneel in de gaten houden** — Bij een echte MCP-aanroep hoort er activiteit rond tooling / MCP in de log mee te lopen (exacte regels hangen van Hermes-versie en logniveau af).
4. **Gerichte controle-vraag** (minimale ruimte voor “verkeerde” tool-routing):

   ```text
   Voer een search uit met de tool search_knowledge op de query 'VWO Elite' en vertel me wat het is en wanneer het lanceert.
   ```

   Als sessie en ingestie kloppen, hoort het antwoord de **exacte zin uit `test.txt`** (rooktestdata) te bevatten — niet een algemene VWO-marketingpagina van het web.

## Changelog (technisch)

- `ingest_state.py`, `orphan_cleanup.py`, `subtitle_sidecar.py`, `ingest_handlers.py`: incrementele ingest, orphan cleanup, ondertitel-prioriteit, pandoc-fallback.
- `source_formats.py` + `ingest_config.py`: volledige Office/OpenDocument-dekking, media, ondertitels, uitsluitingen en max. bestandsgrootte; `ingest.py` importeert centrale sets.
- `ingest.py`: uitgebreide extensiematrix (Excel incl. `.xls`/`.xlsm`, PowerPoint `.pptx`, CSV, web `.html`/`.htm`, `.xml`, Outlook `.msg`); één MarkItDown-route via `_MARKITDOWN_SUFFIXES`.
- `ingest.py`: PDF en DOCX via **MarkItDown** (`MarkItDown().convert` → `text_content`); statische import (fail fast); overslaan bij lege conversie-output.
- `ingest.py`: semantische chunking i.p.v. vast woordvenster (koppen, `\n\n`, zinnen; code-fences; `DEFAULT_MAX_WORDS = 400`).
- `list_tables()` i.p.v. deprecated `table_names()` (via `list_all_table_names` in `kb_schema.py`).
- Sentence-transformers registry: `registry.create(name=...)` i.p.v. verwijderde `get_text_embedding_function`.
- MCP: ontbrekende `knowledge_base` → lege tabel met `KnowledgeSchema` (stderr-log, geen stdout die stdio JSON breekt).
