# Workspace Wiki & Vault Structures

Canonical vault: `C:/Users/jamel/Documents/Hermes Knowledge` (`OBSIDIAN_VAULT_PATH` = `WIKI_PATH` = `KNOWLEDGE_BASE_PATH`).

Sync naar alle profiel-`.env`: `windows/SYNC_HERMES_API_ENV.bat` (ook in `UPDATE_HERMES.bat` en `POST_GIT_PULL.bat`).

## Layout (fork, 2026-05)

```
Hermes Knowledge/
  README.md
  SCHEMA.md
  index.md
  user-preferences.md
  log.md
  projects/{legal,institutional,ict}/
  indexes/index.md
```

## Rules

- Official sources → RAG (`search_knowledge`), not vault copies.
- Layer 3 (Honcho/Mem0): off on production profiles.
- See `docs/MEMORY_ARCHITECTURE.md` and vault `README.md` for L1-L4 split.
