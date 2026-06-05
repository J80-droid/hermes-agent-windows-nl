"""Unit tests for overlay process_command slash-command patches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from overlay.bootstrap import install
from overlay.hermes_cli.cli_command_patches import (
    _resolve_cost_command,
    _resolve_tps_command,
    apply_cli_command_patches,
)

install()


class TestResolveCommands:
    def test_resolve_cost_and_tps_basics(self):
        assert _resolve_cost_command("/cost on")
        assert _resolve_cost_command("cost status")
        assert not _resolve_cost_command("/model")
        assert _resolve_tps_command("/tps toggle")
        assert _resolve_tps_command("tps")
        assert not _resolve_tps_command("")


def _bare_cli():
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.config = MagicMock()
    cli.config.get.return_value = {}
    return cli


class TestProcessCommandPatch:
    def test_cost_status_returns_true(self):
        from cli import HermesCLI

        apply_cli_command_patches()
        cli = _bare_cli()
        cli._show_cost = True
        cli._cost_bar_mode = "rich"
        cli._invalidate = MagicMock()
        with patch("cli._cprint"):
            ok = HermesCLI.process_command(cli, "/cost status")
        assert ok is True

    def test_tps_status_returns_true(self):
        from cli import HermesCLI

        apply_cli_command_patches()
        cli = _bare_cli()
        cli._show_status_bar_tps = True
        cli._invalidate = MagicMock()
        with patch("cli._cprint"):
            ok = HermesCLI.process_command(cli, "/tps status")
        assert ok is True

    def test_tps_toggle_persists(self):
        from cli import HermesCLI

        apply_cli_command_patches()
        cli = _bare_cli()
        cli._show_status_bar_tps = True
        cli._invalidate = MagicMock()
        with patch("cli._cprint"), patch("cli.save_config_value", return_value=True):
            ok = HermesCLI.process_command(cli, "/tps off")
        assert ok is True
        assert cli._show_status_bar_tps is False

    def test_apply_idempotent(self):
        apply_cli_command_patches()
        from cli import HermesCLI

        first = HermesCLI.process_command
        apply_cli_command_patches()
        assert HermesCLI.process_command is first
