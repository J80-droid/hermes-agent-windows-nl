# Wiki Schema

## Domain

General Knowledge & Workspace Intelligence (Hermes agent vault).

## Conventions

- File names: lowercase, hyphens, no spaces (e.g. `hermes-architecture.md`)
- Every wiki page starts with YAML frontmatter
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- Every new page must be listed in [[index]]
- Every action must be appended to [[log]]

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: []
sources: []
---
```

## Memory layers (Hermes)

| Laag | Locatie | Gebruik |
|------|---------|---------|
| L1 | `%LOCALAPPDATA%\hermes\profiles\<profiel>\memories\` | USER.md + MEMORY.md (caps, frozen snapshot) |
| L2 | `state.db` | session_search — eerdere chats |
| L3 | — | **Uit** — geen Honcho/Mem0 op productie-profielen |
| L4 | Deze vault (`OBSIDIAN_VAULT_PATH`) | Projectnotities, wikilinks |
| RAG | `%USERPROFILE%\data\lancedb\<domein>` | Bron-PDF's, jurisprudentie |

Zie [[user-preferences]] voor stijl buiten de L1-cap.
