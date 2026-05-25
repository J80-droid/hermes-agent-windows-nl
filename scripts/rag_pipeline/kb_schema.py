"""Gedeeld LanceDB-schema en padconstanten voor ingest en MCP-server."""

from rag_log_quiet import apply_torch_ingest_quiet

apply_torch_ingest_quiet()

import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

from lancedb_storage import resolve_lancedb_path

DB_PATH = resolve_lancedb_path()
TABLE_NAME = "knowledge_base"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_registry = get_registry().get("sentence-transformers")
_embedding_function = _registry.create(name=EMBEDDING_MODEL_NAME)


class KnowledgeSchema(LanceModel):
    """Het strikt getypeerde schema voor de vector-database (deterministische `id` voor upsert)."""

    id: str
    text: str = _embedding_function.SourceField()
    vector: Vector(_embedding_function.ndims()) = _embedding_function.VectorField()
    source: str


def list_all_table_names(db: lancedb.DBConnection) -> list[str]:
    """Alle tabelnamen (met paginatie) — LanceDB `list_tables()` i.p.v. deprecated `table_names()`."""
    names: list[str] = []
    page_token = None
    while True:
        resp = db.list_tables(page_token=page_token)
        names.extend(resp.tables)
        page_token = resp.page_token
        if not page_token:
            break
    return names
