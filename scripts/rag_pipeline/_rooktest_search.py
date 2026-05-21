"""Rooktest search_knowledge (zonder inference-API)."""
import os
import sys

os.environ["HERMES_LANCEDB_PATH"] = os.path.expanduser(r"~\data\lancedb\legal")
from kb_schema import DB_PATH
from mcp_server import reset_knowledge_table_cache, search_knowledge

reset_knowledge_table_cache()
print("DB:", DB_PATH)
q = "actieve zorgplicht P-Direkt"
print("QUERY:", q)
result = search_knowledge(q, limit=5)
print(result)
if "Geen resultaten" in result or "Fout bij" in result:
    sys.exit(1)
sys.exit(0)
