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
|--------|-----|
| `origin` | `https://github.com/J80-droid/hermes-agent-windows-nl.git` |
| `upstream` | `https://github.com/NousResearch/hermes-agent.git` |

Ontbreekt `upstream`:

```cmd
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch upstream
```

---

## Standaard sync (aanbevolen: merge)

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent

git fetch upstream
git fetch origin

git status
git merge upstream/main
```

Na conflicten oplossen:

```cmd
git push origin main
```

Daarna in dezelfde repo:

```cmd
windows\hermes_update.bat
```

of `hermes update` (met conda/venv actief).

**Nieuwe Hermes-sessie** starten na grote updates.

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

| Gedrag | Uitleg |
|--------|--------|
| Pull van `origin` | Ja — jouw fork op GitHub |
| Automatisch `upstream/main` mergen | **Nee** als je fork **eigen commits** heeft (RAG/Windows) — Hermes beschermt je wijzigingen |
| Stash lokale wijzigingen | Kan — kies bij prompt **y** alleen als je lokale edits wilt behouden |

Bij melding *“Your fork has N commits not on upstream”*: voer handmatig **`git merge upstream/main`** uit (dit document).

---

## Conflicten: waar je ze verwacht

Bij merge van Nous in jouw fork botsen vaak **jouw fork-only** paden met upstream-wijzigingen.

### Hoge prioriteit (RAG — meestal **jouw versie behouden**)

| Pad | Richtlijn |
|-----|-----------|
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
|-----|-----------|
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

## Na elke upstream-merge (checklist)

1. `git status` — geen onopgeloste conflicten.
2. `pytest tests/rag_pipeline/ -q -m "not rag_integration"`
3. `windows\scripts\install_rag_extras.ps1` (MCP + deps)
4. `windows\scripts\which_hermes_repo.ps1` — `lancedb-knowledge: JA`
5. Optioneel: `windows\hermes_update.bat`
6. Nieuwe Hermes-sessie; rooktest: `search_knowledge` (zie `scripts/rag_pipeline/ACTIVATION.md`)

---

## Snelle status

```cmd
git fetch upstream
git rev-list --left-right --count HEAD...upstream/main
```

Uitvoer `A	B`:

- **A** = commits op jouw branch die upstream niet heeft (jouw fork-werk).
- **B** = commits op upstream die jij nog niet hebt (**achterstand op Nous**).

Grote **B** → plan een merge.

---

## Gerelateerd

- `windows/INSTITUTIONAL.md` — Windows + één checkout
- `scripts/rag_pipeline/ACTIVATION.md` — RAG ingest/MCP/rooktest
- `memory-bank/progress.md` — operationele voortgang
