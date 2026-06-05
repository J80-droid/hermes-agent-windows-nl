#!/usr/bin/env python3
"""Smoke: classic CLI status bar throughput (tok/s) hooks + formatter."""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch


def _make_cli(*, show_tps: bool = True, last_call_tps: float | None = 42.0):
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.model = "anthropic/claude-sonnet-4-20250514"
    cli.session_start = datetime.now() - timedelta(minutes=5)
    cli.conversation_history = [{"role": "user", "content": "hi"}]
    cli._show_cost = True
    cli._show_status_bar_tps = show_tps
    cli._cost_bar_mode = "rich"
    cli._status_bar_visible = True
    cli._invalidate = lambda *args, **kwargs: None
    cli._stream_tps_started_at = None
    cli._stream_tps_tokens_est = 0
    cli._last_call_tps = last_call_tps
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
        _stream_gen_started_at=None,
        _stream_gen_tokens_est=0,
        _last_call_tps=55.0,
        get_rate_limit_state=lambda: None,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=12_450,
            context_length=200_000,
            compression_count=0,
        ),
    )
    return cli


def _smoke_wide_shows_tps_after_cost() -> None:
    cli = _make_cli()
    usage = {
        "calls": 7,
        "cost_status": "estimated",
        "cost_usd": 5.74,
        "session_tools_executed": 12,
    }
    with patch(
        "hermes_cli.usage_snapshot.build_session_usage_snapshot",
        return_value=usage,
    ):
        text = cli._build_status_bar_text(width=120)
    assert "tok/s" in text, text
    assert "$" in text, text
    cost_idx = text.find("$")
    tps_idx = text.find("tok/s")
    assert cost_idx >= 0 and tps_idx > cost_idx, text


def _smoke_narrow_hides_tps() -> None:
    cli = _make_cli()
    text = cli._build_status_bar_text(width=60)
    assert "tok/s" not in text, text


def _smoke_toggle_off() -> None:
    cli = _make_cli(show_tps=False)
    text = cli._build_status_bar_text(width=120)
    assert "tok/s" not in text, text


def _smoke_live_snapshot_from_agent() -> None:
    cli = _make_cli(last_call_tps=None)
    cli.agent._stream_gen_started_at = time.time() - 2.0
    cli.agent._stream_gen_tokens_est = 200
    snap = cli._get_status_bar_snapshot()
    assert snap.get("stream_tps") is not None and snap["stream_tps"] >= 50, snap
    assert snap.get("last_call_tps") == 55.0, snap


def _smoke_freeze_does_not_clobber_agent_tps() -> None:
    cli = _make_cli(last_call_tps=None)
    cli._stream_tps_started_at = time.time() - 1.0
    cli._stream_tps_tokens_est = 80
    cli.agent._last_call_tps = 99.0
    cli._freeze_stream_tps_segment()
    assert cli.agent._last_call_tps == 99.0
    assert cli._last_call_tps is None


def _smoke_nan_rejected() -> None:
    from overlay.bootstrap import install

    install()
    from hermes_cli.status_bar_throughput import format_status_bar_tps

    assert format_status_bar_tps(float("nan")) is None
    assert format_status_bar_tps(math.inf) is None


def main() -> int:
    from overlay.bootstrap import install

    install()
    checks = [
        _smoke_wide_shows_tps_after_cost,
        _smoke_narrow_hides_tps,
        _smoke_toggle_off,
        _smoke_live_snapshot_from_agent,
        _smoke_freeze_does_not_clobber_agent_tps,
        _smoke_nan_rejected,
    ]
    for fn in checks:
        fn()
    print("status_bar_throughput_classic_cli_smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
