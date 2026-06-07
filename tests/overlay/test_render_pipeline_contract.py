"""Production contracts: single normalize, finalize-only streaming (no per-chunk Rich)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hermes_cli.display_markdown import StreamingRenderer, format_response_ansi


def test_format_response_ansi_normalizes_once():
    md = "## Functionele requirements\n| ID | Req |\n|---|---|\n| FR-1 | X |\n"
    with patch(
        "hermes_cli.display_markdown.normalize_assistant_markdown",
        side_effect=lambda text, **kwargs: text,
    ) as mock_norm:
        format_response_ansi(md, cols=100)
    assert mock_norm.call_count == 1


def test_streaming_renderer_feed_never_renders_ansi():
    renderer = StreamingRenderer(cols=100)
    with patch("hermes_cli.display_markdown.format_response_ansi") as mock_fmt:
        for chunk in ("## Kop\n", "tekst\n", "| A |\n"):
            assert renderer.feed(chunk) is None
        assert mock_fmt.call_count == 0


def test_streaming_renderer_finish_renders_once():
    renderer = StreamingRenderer(cols=100)
    renderer.feed("## Functionele requirements\nBody.\n")
    with patch(
        "hermes_cli.display_markdown.format_response_ansi", return_value="ansi"
    ) as mock_fmt:
        out = renderer.finish()
    assert out == "ansi"
    assert mock_fmt.call_count == 1


def test_strict_render_rejects_unprepared_institutional():
    from hermes_cli.institutional_render import render_institutional_assistant

    with patch.dict("os.environ", {"HERMES_STRICT_RENDER": "1"}, clear=False):
        with pytest.raises(ValueError, match="already_normalized"):
            render_institutional_assistant("## Test\nBody", already_normalized=False)


def test_render_institutional_from_prepared_skips_normalize():
    from hermes_cli.institutional_render import render_institutional_from_prepared

    with patch(
        "hermes_cli.institutional_render.normalize_assistant_markdown"
    ) as mock_norm:
        render_institutional_from_prepared("## Test\nBody")
    mock_norm.assert_not_called()
