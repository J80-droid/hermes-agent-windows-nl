"""argparse_fork_patch: config get subcommand registration."""

from __future__ import annotations

import argparse

import pytest

from overlay.hermes_cli.argparse_fork_patch import apply_argparse_fork_patch


@pytest.fixture(autouse=True)
def _fresh_argparse_patch() -> None:
    """Elke test krijgt een schone patch (idempotent in productie, geïsoleerd in tests)."""
    apply_argparse_fork_patch()
    yield


def test_config_get_registered_once() -> None:
    root = argparse.ArgumentParser()
    config = root.add_subparsers(dest="config_command")
    config.add_parser("show")
    config.add_parser("migrate")
    assert "get" in config.choices
    get_p = config.choices["get"]
    action_dests = {getattr(a, "dest", None) for a in get_p._actions}
    assert "config_key" in action_dests


def test_upstream_get_not_duplicated() -> None:
    root = argparse.ArgumentParser()
    config = root.add_subparsers(dest="config_command")
    upstream_get = config.add_parser("get", help="upstream")
    upstream_get.add_argument("config_key")
    config.add_parser("show")
    assert len([n for n in config.choices if n == "get"]) == 1


def test_get_registered_before_show_when_get_is_first() -> None:
    root = argparse.ArgumentParser()
    config = root.add_subparsers(dest="config_command")
    config.add_parser("get").add_argument("config_key")
    config.add_parser("show")
    assert "get" in config.choices
    assert len(config.choices) == 2


def test_config_subparser_does_not_get_profile_use_flags() -> None:
    root = argparse.ArgumentParser()
    config = root.add_subparsers(dest="config_command")
    show_p = config.add_parser("show")
    option_strings = {opt for a in show_p._actions for opt in (a.option_strings or [])}
    assert "--fix-hermes-home" not in option_strings
    assert "get" in config.choices


def test_profile_use_gets_fork_flags() -> None:
    root = argparse.ArgumentParser()
    profile = root.add_subparsers(dest="profile_action")
    use_p = profile.add_parser("use")
    option_strings = {opt for a in use_p._actions for opt in (a.option_strings or [])}
    assert "--fix-hermes-home" in option_strings
    assert "--no-restart-gateway" in option_strings


def test_apply_patch_idempotent() -> None:
    apply_argparse_fork_patch()
    apply_argparse_fork_patch()
    root = argparse.ArgumentParser()
    config = root.add_subparsers(dest="config_command")
    config.add_parser("edit")
    assert "get" in config.choices


def test_wrong_dest_no_get_injected() -> None:
    root = argparse.ArgumentParser()
    other = root.add_subparsers(dest="other_command")
    other.add_parser("show")
    assert "get" not in other.choices
