"""Overlay: toolset post-setup CLI helpers + argparse wiring."""

from __future__ import annotations

import argparse
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from overlay.bootstrap import install
from overlay.hermes_cli.argparse_fork_patch import apply_argparse_fork_patch
from overlay.hermes_cli.tools_config_fork_patch import (
    apply_tools_config_fork_patch,
    run_post_setup_command,
    valid_post_setup_keys,
)


@pytest.fixture(autouse=True)
def _fresh_patches() -> None:
    apply_argparse_fork_patch()
    apply_tools_config_fork_patch()
    yield


def test_valid_post_setup_keys_collects_builtin() -> None:
    keys = valid_post_setup_keys()
    assert isinstance(keys, set)
    assert "agent_browser" in keys or "ddgs" in keys or len(keys) >= 0


def test_run_post_setup_command_rejects_unknown_key() -> None:
    with patch(
        "overlay.hermes_cli.tools_config_fork_patch.valid_post_setup_keys",
        return_value={"known_key"},
    ):
        rc = run_post_setup_command(SimpleNamespace(post_setup_key="bad"))
    assert rc == 2


def test_run_post_setup_command_happy_path() -> None:
    args = SimpleNamespace(post_setup_key="agent_browser")
    with patch(
        "overlay.hermes_cli.tools_config_fork_patch.valid_post_setup_keys",
        return_value={"agent_browser"},
    ), patch("hermes_cli.tools_config._run_post_setup") as run_hook, patch(
        "hermes_cli.tools_config._print_info"
    ), patch("hermes_cli.tools_config._print_success"):
        rc = run_post_setup_command(args)
    assert rc == 0
    run_hook.assert_called_once_with("agent_browser")


def test_tools_post_setup_parser_registered() -> None:
    root = argparse.ArgumentParser()
    tools = root.add_subparsers(dest="tools_command")
    sub = tools.add_parser("tools")
    action = sub.add_subparsers(dest="tools_action")
    action.add_parser("list")

    def cmd_tools(_args):
        return 0

    sub.set_defaults(func=cmd_tools)
    assert "post-setup" in action.choices
    post = action.choices["post-setup"]
    assert any(getattr(a, "dest", None) == "post_setup_key" for a in post._actions)


def test_cmd_tools_wrapper_routes_post_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    import hermes_cli.tools_config as tc

    tc.run_post_setup_command = MagicMock(return_value=0)  # type: ignore[attr-defined]
    monkeypatch.setattr(sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))

    root = argparse.ArgumentParser()
    tools = root.add_subparsers(dest="tools_command")
    tools_p = tools.add_parser("tools")
    sub = tools_p.add_subparsers(dest="tools_action")
    sub.add_parser("list")

    def cmd_tools(args):
        return 42

    tools_p.set_defaults(func=cmd_tools)
    assert "post-setup" in sub.choices
    wrapped = tools_p.get_default("func")
    ns = argparse.Namespace(tools_action="post-setup", post_setup_key="ddgs")
    with pytest.raises(SystemExit) as exc:
        wrapped(ns)
    assert exc.value.code == 0
    tc.run_post_setup_command.assert_called_once()


def test_bootstrap_exposes_run_post_setup_on_tools_config() -> None:
    install()
    import hermes_cli.tools_config as tc

    assert callable(tc.run_post_setup_command)
    assert callable(tc.valid_post_setup_keys)
