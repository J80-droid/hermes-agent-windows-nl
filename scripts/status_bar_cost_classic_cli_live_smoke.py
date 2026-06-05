#!/usr/bin/env python3
"""Live-path smoke: classic CLI status bar after one completed turn.

Exercises the same code path as `hermes chat` (cli.py snapshot + fragments)
without a PTY: models post-turn agent counters, real usage_snapshot pricing,
/cost toggle, and optional subprocess isolation check.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_overlay() -> None:
    try:
        from overlay.bootstrap import install

        install()
    except Exception:
        pass


def _make_post_turn_cli(*, show_cost: bool = True):
    _ensure_overlay()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.model = "anthropic/claude-sonnet-4-20250514"
    cli.session_start = datetime.now() - timedelta(minutes=1)
    cli.conversation_history = [
        {"role": "user", "content": "ping"},
        {"role": "assistant", "content": "pong"},
    ]
    cli._show_cost = show_cost
    cli._cost_bar_mode = "rich"
    cli._status_bar_visible = True
    cli._invalidate = lambda *args, **kwargs: None
    cli.agent = SimpleNamespace(
        model=cli.model,
        provider="anthropic",
        base_url="",
        session_input_tokens=1_000,
        session_output_tokens=200,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_prompt_tokens=1_000,
        session_completion_tokens=200,
        session_total_tokens=1_200,
        session_api_calls=1,
        get_rate_limit_state=lambda: None,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=1_200,
            context_length=200_000,
            compression_count=0,
        ),
    )
    return cli


def _status_bar_fragments_text(cli, *, width: int = 120) -> str:
    mock_app = MagicMock()
    mock_app.output.get_size.return_value = MagicMock(columns=width)
    with patch("prompt_toolkit.application.get_app", return_value=mock_app):
        frags = cli._get_status_bar_fragments()
    return "".join(text for _, text in frags)


def smoke_post_turn_snapshot_has_usage() -> None:
    cli = _make_post_turn_cli()
    snapshot = cli._get_status_bar_snapshot()
    usage = snapshot.get("usage") or {}
    assert usage.get("calls", 0) >= 1, snapshot
    assert snapshot.get("session_api_calls") == 1


def smoke_post_turn_status_bar_shows_cost_after_session_metrics() -> None:
    cli = _make_post_turn_cli()
    text = cli._build_status_bar_text(width=120)
    assert "$" in text, text
    pct_idx = text.find("%")
    cost_idx = text.find("$")
    assert pct_idx >= 0 and cost_idx > pct_idx, text

    mock_app = MagicMock()
    mock_app.output.get_size.return_value = MagicMock(columns=120)
    with patch("prompt_toolkit.application.get_app", return_value=mock_app):
        frags = cli._get_status_bar_fragments()
    frag_text = "".join(value for _, value in frags)
    assert "$" in frag_text, frag_text
    assert "claude-sonnet" in frag_text
    cost_styles = [style for style, value in frags if "$" in value]
    assert cost_styles and cost_styles[0] == "class:status-bar-cost", frags


def smoke_post_turn_cost_toggle_hides_bar() -> None:
    cli = _make_post_turn_cli()
    assert "$" in cli._build_status_bar_text(width=120)

    with patch("cli.save_config_value", return_value=True):
        cli._handle_cost_command("/cost off")
    assert cli._show_cost is False

    text = cli._build_status_bar_text(width=120)
    frag_text = _status_bar_fragments_text(cli, width=120)
    assert "$" not in text, text
    assert "$" not in frag_text, frag_text

    with patch("cli.save_config_value", return_value=True):
        cli._handle_cost_command("/cost on")
    assert cli._show_cost is True
    assert "$" in cli._build_status_bar_text(width=120)


def smoke_gemini_35_flash_cache_cost_not_na() -> None:
    """Regression: gemini-3.5-flash + cache hits must show $ estimate, not n/a."""
    _ensure_overlay()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.model = "gemini-3.5-flash"
    cli.session_start = datetime.now() - timedelta(minutes=3)
    cli.conversation_history = [
        {"role": "user", "content": "audit memory"},
        {"role": "assistant", "content": "ok"},
    ]
    cli._show_cost = True
    cli._cost_bar_mode = "rich"
    cli._status_bar_visible = True
    cli._invalidate = lambda *args, **kwargs: None
    cli.agent = SimpleNamespace(
        model="gemini-3.5-flash",
        provider="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        session_input_tokens=5_000,
        session_output_tokens=500,
        session_cache_read_tokens=16_000,
        session_cache_write_tokens=0,
        session_prompt_tokens=21_000,
        session_completion_tokens=500,
        session_total_tokens=21_500,
        session_api_calls=11,
        session_estimated_cost_usd=0.0144,
        session_cost_status="estimated",
        get_rate_limit_state=lambda: None,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=31_500,
            context_length=1_000_000,
            compression_count=0,
        ),
    )

    snapshot = cli._get_status_bar_snapshot()
    usage = snapshot.get("usage") or {}
    assert usage.get("cost_status") == "estimated", usage
    assert usage.get("cost_usd") is not None, usage

    text = cli._build_status_bar_text(width=120)
    frag_text = _status_bar_fragments_text(cli, width=120)
    assert "gemini-3.5-flash" in text, text
    assert "$" in text, text
    assert "n/a" not in text, text
    assert "$" in frag_text, frag_text
    assert "n/a" not in frag_text, frag_text


def smoke_subprocess_isolated_import() -> None:
    repo = _repo_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    env["HERMES_QUIET"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "status_bar_cost_classic_cli_live_smoke.py"),
            "--in-process-only",
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    combined = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0:
        raise AssertionError(
            "subprocess live smoke failed\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    assert "classic cli live status bar cost smoke ok" in combined, combined


def run_in_process_smokes() -> None:
    smoke_post_turn_snapshot_has_usage()
    smoke_post_turn_status_bar_shows_cost_after_session_metrics()
    smoke_post_turn_cost_toggle_hides_bar()
    smoke_gemini_35_flash_cache_cost_not_na()


def main() -> None:
    parser = argparse.ArgumentParser(description="Classic CLI live status-bar cost smoke")
    parser.add_argument(
        "--in-process-only",
        action="store_true",
        help="Skip subprocess isolation check (internal)",
    )
    args = parser.parse_args()

    run_in_process_smokes()
    if not args.in_process_only:
        smoke_subprocess_isolated_import()
    print("classic cli live status bar cost smoke ok", flush=True)


if __name__ == "__main__":
    main()
