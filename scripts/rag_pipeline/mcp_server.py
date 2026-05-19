import sys

import lancedb
from mcp.server.fastmcp import FastMCP

from kb_schema import DB_PATH, TABLE_NAME, KnowledgeSchema, list_all_table_names

mcp = FastMCP("LanceDB-Knowledge-Server")

db = lancedb.connect(DB_PATH)


def _ensure_knowledge_table():
    """Opent `knowledge_base` of maakt een lege tabel met KnowledgeSchema aan (geen crash)."""
    if TABLE_NAME in list_all_table_names(db):
        return db.open_table(TABLE_NAME)
    print(
        f"[INFO] Tabel '{TABLE_NAME}' ontbreekt — lege tabel initialiseren met KnowledgeSchema.",
        file=sys.stderr,
    )
    return db.create_table(TABLE_NAME, schema=KnowledgeSchema)


table = _ensure_knowledge_table()


@mcp.tool()
def search_knowledge(query: str, limit: int = 5) -> str:
    """
    Zoekt in de lokale LanceDB database naar relevante informatie.
    Gebruik dit wanneer je diepgaande data nodig hebt uit de GB's aan opgeslagen bestanden.
    """
    try:
        results = table.search(query).limit(limit).to_list()

        output = []
        for res in results:
            output.append(
                f"Bron: {res.get('source', 'Onbekend')}\nInhoud: {res.get('text', '')}"
            )

        return "\n---\n".join(output) if output else "Geen resultaten gevonden."
    except Exception as e:
        return f"Fout bij doorzoeken database: {str(e)}"


if __name__ == "__main__":
    mcp.run()
