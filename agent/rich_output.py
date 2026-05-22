"""Bridge TUI gateway rendering to the same Rich markdown path as the classic CLI."""

from __future__ import annotations

from hermes_cli.display_markdown import (
    StreamingRenderer,
    format_response_ansi,
    skin_markdown_theme,
)

__all__ = [
    "StreamingRenderer",
    "format_response",
    "skin_markdown_theme",
]


def format_response(text: str, cols: int = 80) -> str | None:
    """Return ANSI-rendered assistant markdown for ``tui_gateway.render``."""
    return format_response_ansi(text, cols)
