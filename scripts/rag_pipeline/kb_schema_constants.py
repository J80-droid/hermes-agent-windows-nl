"""Lightweight knowledge-base constants (no LanceDB / torch import)."""

from __future__ import annotations

TABLE_NAME = "knowledge_base"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def get_db_path() -> str:
    """Resolve the active LanceDB directory from environment/domain defaults."""
    from vector_store_paths import resolve_lancedb_path

    return resolve_lancedb_path()
