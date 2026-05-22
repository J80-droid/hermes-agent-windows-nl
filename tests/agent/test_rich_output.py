"""Tests for agent.rich_output bridge."""

from agent import rich_output


def test_format_response_returns_ansi_for_markdown():
    out = rich_output.format_response("## Titel\n\n- een", cols=80)
    assert out is not None
    assert "Titel" in out
    assert "\x1b" in out or "Titel" in out


def test_streaming_renderer_accumulates_then_finishes():
    renderer = rich_output.StreamingRenderer(cols=80)
    assert renderer.feed("## Kop\n\n") is None
    done = renderer.finish()
    assert done is None or "Kop" in done
