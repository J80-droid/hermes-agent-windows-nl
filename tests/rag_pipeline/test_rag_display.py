from rag_display import inline_citeer_sjabloon, source_basename, wrap_bron_citations_for_markdown_display


def test_source_basename_windows_path():
    assert source_basename(r"04_Legal\map\brief.pdf") == "brief.pdf"


def test_inline_citeer_sjabloon():
    assert inline_citeer_sjabloon(r"a\b\c.docx") == "[Bron: c.docx]"


def test_wrap_bron_citations_idempotent():
    raw = "Feit [Bron: brief.pdf] en `al [Bron: x]` backtick."
    out = wrap_bron_citations_for_markdown_display(raw)
    assert "`[Bron: brief.pdf]`" in out
    assert "`al [Bron: x]`" in out
    assert "``" not in out.replace("`al [Bron: x]`", "")
