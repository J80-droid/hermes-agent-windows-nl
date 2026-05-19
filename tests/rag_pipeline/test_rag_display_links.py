import os
from pathlib import Path

from rag_display import bron_file_uri, inline_citeer_sjabloon


def test_inline_citeer_with_file_link(tmp_path, monkeypatch):
    f = tmp_path / "brief.pdf"
    f.write_bytes(b"x")
    monkeypatch.setenv("HERMES_RAG_RAW_SOURCE", str(tmp_path))
    monkeypatch.setenv("HERMES_RAG_BRON_FILE_LINKS", "1")
    cite = inline_citeer_sjabloon("brief.pdf")
    assert cite.startswith("[Bron: brief.pdf](")
    assert cite.endswith(")")
    assert bron_file_uri("brief.pdf") == Path(f).as_uri()
