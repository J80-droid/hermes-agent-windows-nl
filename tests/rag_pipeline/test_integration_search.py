"""Integratie: mini-LanceDB + search_knowledge (vereist [rag] / sentence-transformers)."""

from __future__ import annotations

import importlib
import sys

import pytest

pytestmark = pytest.mark.rag_integration


@pytest.fixture
def isolated_rag_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_LANCEDB_PATH", str(tmp_path))
    for name in list(sys.modules):
        if name in ("kb_schema", "mcp_server") or name.startswith("kb_schema.") or name.startswith(
            "mcp_server."
        ):
            del sys.modules[name]
    yield tmp_path
    for name in list(sys.modules):
        if name in ("kb_schema", "mcp_server"):
            del sys.modules[name]


def test_search_knowledge_roundtrip(isolated_rag_db):
    import kb_schema
    import mcp_server
    from kb_schema import DB_PATH, TABLE_NAME, KnowledgeSchema

    importlib.reload(kb_schema)
    importlib.reload(mcp_server)

    mcp_server.reset_knowledge_table_cache()
    import lancedb

    db = lancedb.connect(DB_PATH)
    table = db.create_table(TABLE_NAME, schema=KnowledgeSchema)
    table.add(
        [
            {
                "id": "test-chunk-0",
                "text": "VWO Elite is een geavanceerd platform gebouwd door Jamel. Het lanceert in 2026.",
                "source": "test.txt",
            }
        ]
    )
    mcp_server.reset_knowledge_table_cache()

    out = mcp_server.search_knowledge("VWO Elite", limit=2)
    assert "test.txt" in out
    assert "2026" in out
    assert "inline_citeer_sjabloon: [Bron: test.txt]" in out
