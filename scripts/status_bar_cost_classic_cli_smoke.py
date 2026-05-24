#!/usr/bin/env python3
"""Smoke: classic CLI status bar cost (cli.py hooks + status_bar_cost formatter)."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _make_cli():
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.model = "anthropic/claude-sonnet-4-20250514"
    cli.session_start = datetime.now() - timedelta(minutes=5)
    cli.conversation_history = [{"role": "user", "content": "hi"}]
    cli._show_cost = True
    cli._cost_bar_mode = "rich"
    cli._status_bar_visible = True
    cli._invalidate = lambda *args, **kwargs: None
    cli.agent = SimpleNamespace(
        model=cli.model,
        provider="anthropic",
        base_url="",
        session_input_tokens=10_230,
        session_output_tokens=2_220,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_prompt_tokens=10_230,
        session_completion_tokens=2_220,
        session_total_tokens=12_450,
        session_api_calls=7,
        get_rate_limit_state=lambda: None,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=12_450,
            context_length=200_000,
            compression_count=0,
        ),
    )
    return cli


def _smoke_wide_text_shows_cost() -> None:
    cli = _make_cli()
    text = cli._build_status_bar_text(width=120)
    assert "$" in text, text
    assert "claude-sonnet-4-20250514" in text


def _smoke_medium_width_shows_session_cost() -> None:
    cli = _make_cli()
    text = cli._build_status_bar_text(width=60)
    assert "$" in text, text


def _smoke_narrow_hides_cost() -> None:
    cli = _make_cli()
    text = cli._build_status_bar_text(width=50)
    assert "$" not in text, text


def _smoke_rich_breakdown() -> None:
    cli = _make_cli()
    usage = {
        "calls": 7,
        "cost_breakdown_pct": {"cw": 43, "out": 40, "in": 16, "cr": 1},
        "cost_status": "estimated",
        "cost_usd": 5.74,
        "session_tools_executed": 12,
        "turn_cost_usd": 0.23,
    }
    with patch(
        "hermes_cli.usage_snapshot.build_session_usage_snapshot",
        return_value=usage,
    ):
        text = cli._build_status_bar_text(width=120)
    assert "$0.23 / $5.74" in text, text
    assert "cw 43%" in text, text


def _smoke_fragments_at_wide_width() -> None:
    cli = _make_cli()
    mock_app = MagicMock()
    mock_app.output.get_size.return_value = MagicMock(columns=120)
    with patch("prompt_toolkit.application.get_app", return_value=mock_app):
        frags = cli._get_status_bar_fragments()
    joined = "".join(text for _, text in frags)
    assert "$" in joined, joined


def _smoke_cost_toggle() -> None:
    cli = _make_cli()
    with patch("cli.save_config_value", return_value=True) as mock_save:
        cli._handle_cost_command("/cost off")
    mock_save.assert_called_once_with("display.show_cost", False)
    assert cli._show_cost is False
    text = cli._build_status_bar_text(width=120)
    assert "$" not in text, text


def main() -> None:
    _smoke_wide_text_shows_cost()
    _smoke_medium_width_shows_session_cost()
    _smoke_narrow_hides_cost()
    _smoke_rich_breakdown()
    _smoke_fragments_at_wide_width()
    _smoke_cost_toggle()
    print("classic cli status bar cost smoke ok")


if __name__ == "__main__":
    main()
