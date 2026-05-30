# Legal ingest — metadata fase 2b

## Status

| Fase | Inhoud | Status |
|------|--------|--------|
| **2b.1** | Lens afgeleid uit bronpad (`legal_lens_from_path.py`) | Geïmplementeerd |
| **2b.2** | Kolom `legal_lens` in LanceDB-schema | Uitgesteld (schema-migratie + re-ingest) |

SOUL-lenzen-parity (taxonomie ↔ SOUL-tabel) is **niet** hetzelfde als RAG-filter-parity.

## Pad → lens (2b.1)

| Submap onder `04_Legal_Corporate/` | `legal_lens` id |
|-----------------------------------|-----------------|
| `Arbeidsrecht/` | `arb` |
| `Bestuursrecht/` | `bbk` |
| `Aansprakelijkheid_Letselschade/` | `aanspr` |
| `Klokkenluiders/` | `klok` |
| `Corporate/` | `corp` |

Implementatie: [`scripts/rag_pipeline/legal_lens_from_path.py`](../scripts/rag_pipeline/legal_lens_from_path.py)

Filter bij search: prefix op `source` (relatief pad in chunk), bijv. `04_Legal_Corporate/Arbeidsrecht/`.

## 2b.2 (later)

Alleen na expliciete go/no-go:

1. Kolom `legal_lens: str` in `KnowledgeSchema`
2. `schema_migrate.py` + eenmalige `update_knowledge.bat legal`
3. Documenteer in user `domains.yaml`
