# Hermes Knowledge Vault

**Pad:** `C:/Users/jamel/Documents/Hermes Knowledge`  
**Env:** `OBSIDIAN_VAULT_PATH`, `WIKI_PATH`, `KNOWLEDGE_BASE_PATH` (alle drie gelijk).

**Sync:** na wijziging in `~/.hermes/.env` → `windows\SYNC_HERMES_API_ENV.bat` (alle 13 profiel-`.env` bestanden).

Dit is Layer 4 (Obsidian-skill): gestructureerde markdown met `[[wikilinks]]`. Open deze map in Obsidian via *Open folder as vault*.

## Mapstructuur

```
Hermes Knowledge/
  README.md              ← dit bestand
  SCHEMA.md              ← conventies + geheugenlagen
  index.md               ← catalogus
  user-preferences.md    ← stijl (langer dan USER.md-cap)
  log.md                 ← append-only acties
  projects/
    legal/               ← zaaknotities (geen bron-PDF's)
    institutional/       ← renderer, E2E, presentatie
    ict/                 ← runbooks, architectuur
  indexes/
    index.md             ← MOC over projecten
```

## Wat waar hoort

| Inhoud | Laag |
|--------|------|
| PDF's, jurisprudentie, dossierbronnen | **RAG** (`search_knowledge` / LanceDB) |
| Altijd in system prompt (caps) | **L1** `MEMORY.md` / `USER.md` per profiel |
| "Zeiden we dat in chat X?" | **L2** `session_search` |
| Projectnotities, beslissingen, links | **Deze vault** (obsidian-skill) |
| Gedrag per domein | **SOUL** per profiel |

Geen dubbele waarheid: hetzelfde feit niet in RAG én vault zonder `[Bron: …]` of expliciete labeling.

## Layer 3 (bewust uit)

Geen Honcho, Mem0 of andere externe memory-provider op productie-profielen (`core`, `legal`, `ict`, …). Reden: trust/forensic — gecureerde L1 + SOUL + RAG + deze vault; geen stille cloud-inferentie over gebruikersstijl.

Alleen heroverwegen voor een **los casual experimentprofiel**, niet voor legal/dossierwerk.

## Memory-ritual (na sessie)

1. **L1** — Alleen memory-worthy feiten via `memory(action=add|replace|remove)` of handmatig `USER.md` / `MEMORY.md`. Volgende sessie (`/new`) ziet de wijziging (frozen snapshot).
2. **Vault** — Grote projectcontext: nieuwe of bijgewerkte note onder `projects/<domein>/`, link in [[index]] en regel in [[log]].
3. **Stijl** — Voorkeuren die niet in USER.md-cap passen: [[user-preferences]].
4. **RAG** — Nieuwe officiële bronnen: `raw_source_files` + `RAG_KNOWLEDGE_UPDATE.bat`, niet als vault-kopie.
5. **SOUL/memory-sync** — Na `SYNC_TRUST_RUNTIME` of profielwissel: altijd `/new`.

Zie ook `%LOCALAPPDATA%\hermes\profiles\core\KANBAN_WORKFLOWS.md` sectie *Geheugen (L1–L4)*.

## Gerelateerd

- [[SCHEMA]]
- [[user-preferences]]
- [[indexes/index]]
