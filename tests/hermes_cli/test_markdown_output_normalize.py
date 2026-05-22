"""Tests for institutional markdown layout normalization."""

from hermes_cli.markdown_output_normalize import (
    ensure_heading_line_breaks,
    ensure_section_breaks,
    normalize_assistant_markdown,
    normalize_numbered_headings,
)


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


def test_section_break_before_second_heading():
    raw = "Einde stap één.\n## Stap 2: Volgende"
    out = ensure_section_breaks(raw)
    assert "Einde stap één.\n\n## Stap 2" in out


def test_normalize_numbered_step_to_markdown_heading():
    raw = "1 Stap 1: De acceptatie\nTekst.\n2 Stap 2: Opening"
    out = normalize_numbered_headings(raw)
    assert "## Stap 1: De acceptatie" in out
    assert "## Stap 2: Opening" in out


def test_normalize_assistant_markdown_adds_section_breaks():
    raw = "Intro.\n## Hoofdstuk\n\nBody.\n## Tweede"
    out = normalize_assistant_markdown(raw)
    assert "Body.\n\n## Tweede" in out


def test_normalize_assistant_markdown_idempotent_on_clean_input():
    raw = "## Titel\n\nTekst hier."
    assert normalize_assistant_markdown(raw) == raw
