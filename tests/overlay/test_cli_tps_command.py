"""Unit tests for overlay /tps slash command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from overlay.hermes_cli.cli_tps_command import handle_tps_command


def _cli(**overrides):
    base = dict(
        _show_status_bar_tps=True,
        _invalidate=MagicMock(),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@patch("cli.save_config_value", return_value=True)
def test_tps_status_reports_current_state(mock_save):
    cli = _cli(_show_status_bar_tps=False)
    with patch("cli._cprint") as mock_print:
        handle_tps_command(cli, "/tps status")
    mock_save.assert_not_called()
    out = " ".join(str(c) for c in mock_print.call_args[0])
    assert "OFF" in out
    assert "display.show_status_bar_tps" in out


@patch("cli.save_config_value", return_value=True)
def test_tps_on_persists_and_invalidates(mock_save):
    cli = _cli(_show_status_bar_tps=False)
    with patch("cli._cprint"):
        handle_tps_command(cli, "/tps on")
    assert cli._show_status_bar_tps is True
    mock_save.assert_called_once_with("display.show_status_bar_tps", True)
    cli._invalidate.assert_called_once()


@patch("cli.save_config_value", return_value=True)
def test_tps_toggle_flips_state(mock_save):
    cli = _cli(_show_status_bar_tps=True)
    with patch("cli._cprint"):
        handle_tps_command(cli, "/tps toggle")
    assert cli._show_status_bar_tps is False
    mock_save.assert_called_once_with("display.show_status_bar_tps", False)


@patch("cli.save_config_value", return_value=False)
def test_tps_save_failure_reports_error(mock_save):
    cli = _cli()
    with patch("cli._cprint") as mock_print:
        handle_tps_command(cli, "/tps off")
    out = " ".join(str(c) for c in mock_print.call_args[0])
    assert "Failed to save" in out


def test_tps_invalid_arg_shows_usage():
    cli = _cli()
    with patch("cli._cprint") as mock_print:
        handle_tps_command(cli, "/tps bogus")
    out = " ".join(str(c) for c in mock_print.call_args[0])
    assert "Usage:" in out
