"""Gedeeld LanceDB-schema en padconstanten voor ingest en MCP-server."""

from __future__ import annotations

from typing import Any

from rag_log_quiet import apply_torch_ingest_quiet

apply_torch_ingest_quiet()

from kb_schema_constants import EMBEDDING_MODEL_NAME, TABLE_NAME, get_db_path

_knowledge_schema_class: type | None = None


def get_knowledge_schema() -> type:
    """Lazy-load ``KnowledgeSchema`` (pulls sentence-transformers only when needed)."""
    global _knowledge_schema_class
    if _knowledge_schema_class is None:
        from lancedb.embeddings import get_registry
        from lancedb.pydantic import LanceModel, Vector

        registry = get_registry().get("sentence-transformers")
        embedding_function = registry.create(name=EMBEDDING_MODEL_NAME)

        class KnowledgeSchema(LanceModel):
            """Het strikt getypeerde schema voor de vector-database (deterministische `id` voor upsert)."""

            id: str
            text: str = embedding_function.SourceField()
            vector: Vector(embedding_function.ndims()) = embedding_function.VectorField()
            source: str

        _knowledge_schema_class = KnowledgeSchema
    return _knowledge_schema_class


def list_all_table_names(db: Any) -> list[str]:
    """Alle tabelnamen (met paginatie) — LanceDB ``list_tables()`` i.p.v. deprecated ``table_names()``."""
    names: list[str] = []
    page_token = None
    while True:
        resp = db.list_tables(page_token=page_token)
        names.extend(resp.tables)
        page_token = resp.page_token
        if not page_token:
            break
    return names


def __getattr__(name: str) -> Any:
    if name == "DB_PATH":
        return get_db_path()
    if name == "KnowledgeSchema":
        return get_knowledge_schema()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
