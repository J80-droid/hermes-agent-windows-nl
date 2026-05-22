"""Tests for institutional markdown layout normalization."""

from hermes_cli.markdown_output_normalize import ensure_heading_line_breaks, normalize_assistant_markdown


def test_splits_inline_heading_body():
    raw = "## Geobjectiveerde Analyse Dit is de tekst."
    out = ensure_heading_line_breaks(raw)
    assert "## Geobjectiveerde Analyse\n\n" in out
    assert "Dit is de tekst." in out


def test_splits_bold_label_on_same_line():
    raw = "**Betrokken partijen:** Partij A en B"
    out = ensure_heading_line_breaks(raw)
    assert "**Betrokken partijen:**\n\n" in out
    assert "Partij A en B" in out


def test_normalize_assistant_markdown_idempotent_on_clean_input():
    raw = "## Titel\n\nTekst hier."
    assert normalize_assistant_markdown(raw) == raw
