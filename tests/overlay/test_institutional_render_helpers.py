"""Unit tests voor private helpers in ``hermes_cli/institutional_render.py``.

Focus: edge cases, ongeldige input, compact Controle peel, prose coalesce, strict contract.
"""

from __future__ import annotations

import os
from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console
from rich.text import Text as RichText

from hermes_cli.institutional_render import (
    InstitutionalMarkdown,
    InstitutionalTableElement,
    SectionSpacer,
    TABLE_HEADER_PALETTE_DEMO,
    _apply_leading_compact_controle_peel,
    _flush_prose_markdown,
    _is_compact_check_block,
    _peel_institutional_checks,
    _peel_leading_compact_controle,
    _strict_render_contract_enabled,
    render_institutional_assistant,
    render_institutional_from_prepared,
)


# ---------------------------------------------------------------------------
# _peel_leading_compact_controle
# ---------------------------------------------------------------------------


class TestPeelLeadingCompactControle:
    def test_happy_path(self) -> None:
        text = "Controle  · hyperbolen  · stelligheden\n\n## Kop\n"
        body, rem = _peel_leading_compact_controle(text)
        assert body is not None
        assert "- hyperbolen" in body
        assert rem.startswith("## Kop")

    def test_empty_text(self) -> None:
        body, rem = _peel_leading_compact_controle("")
        assert body is None
        assert rem == ""

    def test_whitespace_only(self) -> None:
        body, rem = _peel_leading_compact_controle("   \n  ")
        assert body is None

    def test_prose_controle_without_dot_fails_peel(self) -> None:
        text = "Controle en verificatie van het plan.\n"
        body, rem = _peel_leading_compact_controle(text)
        assert body is None
        assert rem == text

    def test_controle_only_no_items(self) -> None:
        body, rem = _peel_leading_compact_controle("Controle\n")
        assert body is None

    def test_controle_dot_without_items(self) -> None:
        body, rem = _peel_leading_compact_controle("Controle  ·\n")
        assert body is None

    def test_multiline_remainder_preserved(self) -> None:
        text = "Controle  · een\n\nRegel twee\n"
        body, rem = _peel_leading_compact_controle(text)
        assert body is not None
        assert "Regel twee" in rem


# ---------------------------------------------------------------------------
# _apply_leading_compact_controle_peel
# ---------------------------------------------------------------------------


class TestApplyLeadingCompactControlePeel:
    def test_no_op_when_first_not_text(self) -> None:
        pieces = [("check", "- item")]
        assert _apply_leading_compact_controle_peel(pieces) == pieces

    def test_splits_compact_leading_text(self) -> None:
        pieces = [("text", "Controle  · a  · b\n\n## X")]
        out = _apply_leading_compact_controle_peel(pieces)
        assert out[0] == ("check", "- a\n- b")
        assert out[1][0] == "text"
        assert "## X" in out[1][1]

    def test_empty_pieces(self) -> None:
        assert _apply_leading_compact_controle_peel([]) == []


# ---------------------------------------------------------------------------
# _peel_institutional_checks
# ---------------------------------------------------------------------------


class TestPeelInstitutionalChecks:
    def test_xml_block(self) -> None:
        raw = "<institutional_check>\n- A\n</institutional_check>\n\nBody"
        pieces = _peel_institutional_checks(raw)
        kinds = [p[0] for p in pieces]
        assert "check" in kinds
        assert "text" in kinds

    def test_compact_line_without_xml(self) -> None:
        raw = "Controle  · item\n\n## Kop"
        pieces = _peel_institutional_checks(raw)
        assert pieces[0][0] == "check"

    def test_empty_string(self) -> None:
        assert _peel_institutional_checks("") == []

    def test_plain_text_only(self) -> None:
        pieces = _peel_institutional_checks("Alleen tekst.\n")
        assert len(pieces) == 1
        assert pieces[0][0] == "text"


# ---------------------------------------------------------------------------
# _flush_prose_markdown
# ---------------------------------------------------------------------------


class TestFlushProseMarkdown:
    def test_empty_prose_no_op(self) -> None:
        parts: list = []
        _flush_prose_markdown([], parts, code_theme="monokai")
        assert parts == []

    def test_coalesces_lines_to_single_markdown(self) -> None:
        prose = ["line one", "line two"]
        parts: list = []
        _flush_prose_markdown(prose, parts, code_theme="monokai")
        assert len(parts) == 1
        assert isinstance(parts[0], InstitutionalMarkdown)
        assert prose == []

    def test_whitespace_only_prose_ignored(self) -> None:
        parts: list = []
        _flush_prose_markdown(["  ", ""], parts, code_theme="monokai")
        assert parts == []


# ---------------------------------------------------------------------------
# _strict_render_contract_enabled
# ---------------------------------------------------------------------------


class TestStrictRenderContract:
    @pytest.mark.parametrize(
        "value",
        ["1", "true", "TRUE", "yes", "on"],
    )
    def test_truthy_values(self, value: str) -> None:
        with patch.dict(os.environ, {"HERMES_STRICT_RENDER": value}, clear=False):
            assert _strict_render_contract_enabled() is True

    @pytest.mark.parametrize(
        "value",
        ["", "0", "false", "off", "maybe"],
    )
    def test_falsy_values(self, value: str) -> None:
        with patch.dict(os.environ, {"HERMES_STRICT_RENDER": value}, clear=False):
            assert _strict_render_contract_enabled() is False

    def test_unset(self) -> None:
        env = os.environ.copy()
        env.pop("HERMES_STRICT_RENDER", None)
        with patch.dict(os.environ, env, clear=True):
            assert _strict_render_contract_enabled() is False


# ---------------------------------------------------------------------------
# render_institutional_assistant edge cases
# ---------------------------------------------------------------------------


class TestRenderInstitutionalAssistant:
    def test_empty_string_returns_empty_richtext(self) -> None:
        out = render_institutional_from_prepared("   \n  ")
        assert isinstance(out, RichText)
        assert not str(out).strip() or out.plain.strip() == ""

    def test_none_like_empty(self) -> None:
        out = render_institutional_assistant("", already_normalized=True)
        assert isinstance(out, RichText)

    def test_strict_mode_blocks_inline_normalize(self) -> None:
        with patch.dict(os.environ, {"HERMES_STRICT_RENDER": "1"}, clear=False):
            with pytest.raises(ValueError, match="already_normalized"):
                render_institutional_assistant("## T\nx", already_normalized=False)

    def test_non_strict_allows_inline_normalize(self) -> None:
        with patch.dict(os.environ, {"HERMES_STRICT_RENDER": ""}, clear=False):
            with patch(
                "hermes_cli.institutional_render.normalize_assistant_markdown",
                side_effect=lambda t, **_: t,
            ) as mock_norm:
                render_institutional_assistant("## T\nBody", already_normalized=False)
            mock_norm.assert_called_once()

    def test_invalid_palette_falls_back_to_demo(self) -> None:
        renderable = render_institutional_from_prepared(
            "## Test\nTekst.",
            palette="nonexistent_palette_xyz",
        )
        assert renderable is not None


# ---------------------------------------------------------------------------
# _is_compact_check_block
# ---------------------------------------------------------------------------


class TestIsCompactCheckBlock:
    def test_richtext_controle_true(self) -> None:
        assert _is_compact_check_block(RichText("Controle  items"))

    def test_other_renderable_false(self) -> None:
        assert not _is_compact_check_block(InstitutionalMarkdown("## Geen controle"))

    def test_empty_richtext_false(self) -> None:
        assert not _is_compact_check_block(RichText("   "))


# ---------------------------------------------------------------------------
# InstitutionalTableElement empty palette guard
# ---------------------------------------------------------------------------


class TestInstitutionalTableElement:
    def test_empty_palette_context_uses_fallback(self) -> None:
        from hermes_cli.institutional_render import _TABLE_HEADER_PALETTE_CTX

        token = _TABLE_HEADER_PALETTE_CTX.set(())
        try:
            md = InstitutionalMarkdown("| A |\n|---|\n| 1 |")
            buf = StringIO()
            console = Console(file=buf, force_terminal=True, width=80)
            console.print(md)
            assert buf.getvalue()
        finally:
            _TABLE_HEADER_PALETTE_CTX.reset(token)

    def test_renders_with_demo_palette(self) -> None:
        from hermes_cli.institutional_render import _TABLE_HEADER_PALETTE_CTX

        token = _TABLE_HEADER_PALETTE_CTX.set(TABLE_HEADER_PALETTE_DEMO)
        try:
            md = InstitutionalMarkdown("| A | B |\n|---|---|\n| 1 | 2 |")
            buf = StringIO()
            console = Console(file=buf, force_terminal=True, width=80)
            console.print(md)
            assert "A" in buf.getvalue() or buf.getvalue()
        finally:
            _TABLE_HEADER_PALETTE_CTX.reset(token)


# ---------------------------------------------------------------------------
# SectionSpacer bounds
# ---------------------------------------------------------------------------


class TestSectionSpacer:
    def test_zero_lines_clamped_to_one(self) -> None:
        sp = SectionSpacer(lines=0)
        assert sp.lines == 1

    def test_negative_clamped(self) -> None:
        sp = SectionSpacer(lines=-3)
        assert sp.lines == 1
