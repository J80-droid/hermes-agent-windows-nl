"""Tests for institutional Rich markdown theme (skin gold, extended keys)."""

from hermes_cli.display_markdown import skin_markdown_theme


def test_skin_markdown_theme_uses_gold_palette_not_magenta():
    theme = skin_markdown_theme()
    styles = theme.styles

    assert "markdown.h1" in styles
    assert "markdown.h2" in styles
    assert "markdown.h3" in styles
    assert "markdown.code" in styles
    assert "markdown.link" in styles
    assert "markdown.item.bullet" in styles

    h1 = str(styles["markdown.h1"]).lower()
    assert "magenta" not in h1
    assert "ffd700" in h1


def test_skin_markdown_theme_heading_levels_differ():
    theme = skin_markdown_theme()
    h2 = str(theme.styles["markdown.h2"])
    h3 = str(theme.styles["markdown.h3"])
    assert h2 != h3
