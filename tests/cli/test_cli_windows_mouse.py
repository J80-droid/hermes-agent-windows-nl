"""Windows classic CLI: mouse/scroll defaults for prompt_toolkit."""

import sys
from unittest.mock import patch

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from cli import HermesCLI


def test_cli_mouse_support_off_when_config_says_off():
    assert HermesCLI._cli_prompt_toolkit_mouse_support({"display": {"mouse_tracking": "off"}}) is False


def test_cli_mouse_support_on_for_wheel_preset():
    assert HermesCLI._cli_prompt_toolkit_mouse_support({"display": {"mouse_tracking": "wheel"}}) is True


def test_scroll_key_bindings_use_keys_enum_not_invalid_strings():
    kb = KeyBindings()
    kb.add(Keys.ScrollUp)(lambda e: None)
    kb.add(Keys.ScrollDown)(lambda e: None)
    kb.add("pageup")(lambda e: None)


def test_cli_mouse_support_default_off_on_windows_avoids_overlay():
    with patch.object(sys, "platform", "win32"):
        assert HermesCLI._cli_prompt_toolkit_mouse_support({}) is False
    with patch.object(sys, "platform", "linux"):
        assert HermesCLI._cli_prompt_toolkit_mouse_support({}) is False


def test_run_method_does_not_shadow_module_keys_import():
    """Regression: local `from ... import Keys` in run() caused UnboundLocalError at kb.add(Keys.ScrollUp)."""
    import ast
    from pathlib import Path

    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    tree = ast.parse(cli_py.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            for child in ast.walk(node):
                if isinstance(child, ast.ImportFrom) and child.module == "prompt_toolkit.keys":
                    names = [a.name for a in child.names]
                    assert "Keys" not in names, (
                        "Do not import Keys inside run(); use module-level import"
                    )
            break
    else:
        raise AssertionError("HermesCLI.run not found")
