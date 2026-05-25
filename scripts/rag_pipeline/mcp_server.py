import sys

import lancedb
from mcp.server.fastmcp import FastMCP

from kb_schema import DB_PATH, TABLE_NAME, KnowledgeSchema, list_all_table_names
from lancedb_storage import (
    close_lancedb_connection,
    connect_lancedb,
    register_lancedb_shutdown_hooks,
)
from rag_display import inline_citeer_sjabloon, source_basename

mcp = FastMCP("LanceDB-Knowledge-Server")

_db: lancedb.DBConnection | None = None
_table = None


def _get_db() -> lancedb.DBConnection:
    global _db
    if _db is None:
        _db = connect_lancedb(DB_PATH)
    return _db


def _ensure_knowledge_table():
    """Opent `knowledge_base` of maakt een lege tabel met KnowledgeSchema aan (geen crash)."""
    db = _get_db()
    if TABLE_NAME in list_all_table_names(db):
        return db.open_table(TABLE_NAME)
    print(
        f"[INFO] Tabel '{TABLE_NAME}' ontbreekt — lege tabel initialiseren met KnowledgeSchema.",
        file=sys.stderr,
    )
    return db.create_table(TABLE_NAME, schema=KnowledgeSchema)


def _get_knowledge_table():
    global _table
    if _table is None:
        _table = _ensure_knowledge_table()
    return _table


def close_lancedb_mcp_connection() -> None:
    """Graceful shutdown for MCP subprocess (Windows mmap release)."""
    global _db, _table
    _table = None
    if _db is not None:
        close_lancedb_connection(_db)
        _db = None


def reset_knowledge_table_cache() -> None:
    """Tests/integration: cache legen na wijziging HERMES_LANCEDB_PATH."""
    close_lancedb_mcp_connection()


register_lancedb_shutdown_hooks(extra_cleanup=close_lancedb_mcp_connection)


@mcp.tool()
def search_knowledge(query: str, limit: int = 5) -> str:
    """
    Zoekt in de lokale LanceDB-database naar relevante passages uit geïndexeerde bronbestanden.
    Gebruik dit voor feiten, chronologie en juridische analyse; citeer met [Bron: bestandsnaam].
    """
    if not str(query).strip():
        return "Geen zoekterm opgegeven."
    try:
        safe_limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        safe_limit = 5
    try:
        results = _get_knowledge_table().search(query).limit(safe_limit).to_list()

        output = []
        for res in results:
            source = res.get("source", "Onbekend")
            text = res.get("text", "")
            basename = source_basename(str(source))
            cite = inline_citeer_sjabloon(str(source))
            output.append(
                f"bron_bestand: {basename}\n"
                f"bron_pad: {source}\n"
                f"inline_citeer_sjabloon: {cite}\n"
                f"Inhoud: {text}"
            )

        return "\n---\n".join(output) if output else "Geen resultaten gevonden."
    except Exception as e:
        return f"Fout bij doorzoeken database: {str(e)}"


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        close_lancedb_mcp_connection()
