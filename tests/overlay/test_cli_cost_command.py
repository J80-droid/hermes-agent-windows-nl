"""Unit tests for overlay /cost slash command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from overlay.hermes_cli.cli_cost_command import handle_cost_command


def _cli(**overrides):
    base = dict(
        _show_cost=True,
        _cost_bar_mode="rich",
        _invalidate=MagicMock(),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@patch("cli.save_config_value", return_value=True)
def test_cost_status_reports_mode(mock_save):
    cli = _cli(_show_cost=True, _cost_bar_mode="compact")
    with patch("cli._cprint") as mock_print:
        handle_cost_command(cli, "/cost status")
    mock_save.assert_not_called()
    out = " ".join(str(c) for c in mock_print.call_args[0])
    assert "ON" in out
    assert "compact" in out


@patch("cli.save_config_value", return_value=True)
def test_cost_off_persists(mock_save):
    cli = _cli()
    with patch("cli._cprint"):
        handle_cost_command(cli, "/cost off")
    assert cli._show_cost is False
    mock_save.assert_called_once_with("display.show_cost", False)


@patch("cli.save_config_value", return_value=False)
def test_cost_save_failure(mock_save):
    cli = _cli()
    with patch("cli._cprint") as mock_print:
        handle_cost_command(cli, "/cost on")
    out = " ".join(str(c) for c in mock_print.call_args[0])
    assert "Failed to save" in out
