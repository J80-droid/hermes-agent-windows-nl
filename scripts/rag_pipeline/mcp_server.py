from typing import Any

from mcp.server.fastmcp import FastMCP

from kb_schema import get_db_path
from knowledge_repository import KnowledgeRepository
from vector_store_ports import get_vector_store_backend
from rag_display import inline_citeer_sjabloon, source_basename

mcp = FastMCP("LanceDB-Knowledge-Server")

_repo: KnowledgeRepository | None = None
_db: Any = None
_table: Any = None


def _ensure_mcp_knowledge() -> tuple[KnowledgeRepository, Any]:
    """Single connect path: repo + tracked connection + ensured table."""
    global _repo, _db, _table
    if _repo is not None and _db is not None and _table is not None:
        return _repo, _table
    try:
        if _repo is None:
            _repo = KnowledgeRepository(db_path=get_db_path())
        _db = _repo.backend.connect(get_db_path())
        _table = _repo.ensure_table(_db)
        return _repo, _table
    except Exception:
        close_lancedb_mcp_connection()
        raise


def close_lancedb_mcp_connection() -> None:
    """Graceful shutdown for MCP subprocess (Windows mmap release)."""
    global _db, _table, _repo
    _table = None
    if _db is not None and _repo is not None:
        _repo.backend.close(_db)
        _db = None
    _repo = None


def reset_knowledge_table_cache() -> None:
    """Tests/integration: cache legen na wijziging HERMES_LANCEDB_PATH."""
    close_lancedb_mcp_connection()


# Shutdown hooks on the VectorStore backend (not _get_repo()) — avoids eager repo init at import.
get_vector_store_backend().register_shutdown_hooks(extra_cleanup=close_lancedb_mcp_connection)


@mcp.tool()
def search_knowledge(query: str, limit: int = 5) -> str:
    """
    Zoekt in de lokale LanceDB-database naar relevante passages uit geïndexeerde bronbestanden.
    Gebruik dit voor feiten, chronologie en juridische analyse; citeer met [Bron: bestandsnaam].
    """
    if not str(query).strip():
        return "Geen zoekterm opgegeven."
    try:
        repo, table = _ensure_mcp_knowledge()
        results = repo.search(query, limit=limit, table=table)

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
