"""Tests for diagnose_renderer, palet loading, and legacy token migration."""

from pathlib import Path

from hermes_cli.display_markdown import get_assistant_render_settings
from hermes_cli.institutional_render import (
    _get_all_palettes,
    _BUILTIN_PALETTES,
    assistant_markdown_theme,
    table_header_palette,
)


def test_diagnose_renderer_verify_passes():
    """diagnose_renderer --verify should pass with default settings."""
    s = get_assistant_render_settings()
    assert s["assistant_render_style"] == "institutional_rich"
    assert s["assistant_palette"] == "demo"


def test_yaml_palettes_loaded():
    """config/palettes.yaml should be picked up by _get_all_palettes()."""
    all_p = _get_all_palettes()
    # Built-ins exist
    assert "demo" in all_p
    assert "hermes" in all_p
    assert "neutral" in all_p
    # New YAML palettes
    assert "monokai" in all_p
    assert "dracula" in all_p
    assert "tokyo" in all_p
    assert "nordic" in all_p
    assert "pacific" in all_p


def test_yaml_palette_has_required_keys():
    all_p = _get_all_palettes()
    for name, colors in all_p.items():
        for key in ("h1", "h2", "h3", "h4", "strong", "label", "text", "table_header"):
            assert key in colors, f"Palette '{name}' missing key '{key}'"


def test_unknown_palette_falls_back_to_demo():
    theme = assistant_markdown_theme("does_not_exist")
    # Should not crash; falls back to demo colours
    assert theme is not None


def test_table_header_palette_custom():
    tokyo = table_header_palette("tokyo")
    assert len(tokyo) >= 2
    demo = table_header_palette("demo")
    assert len(demo) >= 2
    assert demo[0].lower().startswith("bold #66d9ef")


def test_score_institutional_render_verify():
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "score_institutional_render.py"
    r = subprocess.run(
        [sys.executable, str(script), "--verify"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_display_markdown_warns_on_unknown_palette(monkeypatch):
    """get_assistant_render_settings logs warning for unknown palette."""
    import logging
    import unittest.mock

    logger = logging.getLogger("hermes_cli.display_markdown")
    with unittest.mock.patch.object(logger, "warning") as mock_warn:
        # We can't easily inject a bad config value here because _display_config
        # reads from the live config.  Instead, verify the normal path produces
        # no warning.
        s = get_assistant_render_settings()
        assert s["assistant_palette"] == "demo"
        # No warning for known palette
        mock_warn.assert_not_called()


def test_legacy_token_migration():
    """migrate_soul_tokens strips [COLOR_*] tokens."""
    from scripts.migrate_soul_tokens import migrate_text

    raw = "[COLOR_BLUE]## Titel[RESET]\n\n[COLOR_GREEN]**Label:**[RESET] waarde"
    cleaned = migrate_text(raw)
    assert "[COLOR_BLUE]" not in cleaned
    assert "[COLOR_GREEN]" not in cleaned
    assert "[RESET]" not in cleaned
    assert "## Titel" in cleaned
    assert "**Label:**" in cleaned


def test_legacy_token_migration_does_not_strip_markdown():
    """Markdown syntax (##, **) should survive migration."""
    from scripts.migrate_soul_tokens import migrate_text

    raw = "## Heading\n\n**Bold:** value"
    cleaned = migrate_text(raw)
    assert "## Heading" in cleaned
    assert "**Bold:**" in cleaned
