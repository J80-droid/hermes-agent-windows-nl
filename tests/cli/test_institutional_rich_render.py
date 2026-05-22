"""Institutional Rich renderer: demo palette, per-column table headers."""

import re

from hermes_cli.display_markdown import format_response_ansi, get_assistant_render_settings
from hermes_cli.institutional_render import assistant_markdown_theme, render_institutional_assistant


def test_assistant_markdown_theme_demo_not_gold():
    theme = assistant_markdown_theme("demo")
    h1 = str(theme.styles["markdown.h1"]).lower()
    assert "ffd700" not in h1
    assert "cyan" in h1


def test_table_render_produces_multiple_header_styles():
    md = (
        "## Overzicht\n\n"
        "| Datum | Titel | Budget |\n"
        "|---|---|---|\n"
        "| 2024 | A | 1 |\n"
    )
    out = format_response_ansi(md, cols=100) or ""
    codes = set(re.findall(r"\x1b\[[0-9;]*m", out))
    assert len(codes) >= 2


def test_render_institutional_assistant_label_block():
    md = "**Stap:**\n\nInhoud van het blok."
    renderable = render_institutional_assistant(md, label_columns=True)
    assert renderable is not None


def test_get_assistant_render_settings_defaults():
    s = get_assistant_render_settings()
    assert s["assistant_render_style"] in {"institutional_rich", "markdown_legacy"}
    assert s["assistant_palette"] in {"demo", "hermes", "neutral"}


def test_render_institutional_assistant_splits_headings():
    md = "## Eerste\n\ntekst\n## Tweede\n\nmeer"
    renderable = render_institutional_assistant(md, already_normalized=True)
    from rich.console import Group

    assert isinstance(renderable, Group)
    assert len(renderable._renderables) >= 3
