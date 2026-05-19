from cli import _wrap_bron_citations_for_display


def test_wrap_bron_citations_for_display_adds_backticks():
    raw = "Feit [Bron: dossier.pdf] hier."
    out = _wrap_bron_citations_for_display(raw)
    assert "`[Bron: dossier.pdf]`" in out


def test_wrap_bron_citations_for_display_idempotent_on_prefixed():
    raw = "Al `[Bron: x.pdf]` ok."
    assert _wrap_bron_citations_for_display(raw) == raw
