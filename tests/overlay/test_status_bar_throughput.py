"""Unit tests for hermes_cli.status_bar_throughput."""

from types import SimpleNamespace

from hermes_cli.status_bar_throughput import (
    compute_call_tps,
    compute_live_tps,
    format_status_bar_tps,
    live_throughput_snapshot,
    resolve_status_bar_throughput_label,
    should_show_status_bar_tps,
)


def test_compute_live_tps_requires_min_elapsed():
    assert compute_live_tps(100, 1000.0, now=1000.2) is None
    assert compute_live_tps(100, 1000.0, now=1001.0) == 100.0


def test_compute_call_tps():
    assert compute_call_tps(0, 2.0) is None
    assert compute_call_tps(50, 1.0) == 50.0
    assert compute_call_tps(10, 0.1) == 20.0


def test_format_status_bar_tps():
    assert format_status_bar_tps(None) is None
    assert format_status_bar_tps(0.5) is None
    assert format_status_bar_tps(42.4) == "42 tok/s"


def test_resolve_prefers_live_over_frozen():
    label = resolve_status_bar_throughput_label(
        {"stream_tps": 80.0, "last_call_tps": 20.0},
        show_tps=True,
        width=120,
    )
    assert label == "80 tok/s"


def test_resolve_frozen_when_no_live():
    label = resolve_status_bar_throughput_label(
        {"stream_tps": None, "last_call_tps": 33.0},
        show_tps=True,
        width=120,
    )
    assert label == "33 tok/s"


def test_resolve_hidden_when_narrow_or_disabled():
    assert resolve_status_bar_throughput_label(
        {"last_call_tps": 40.0},
        show_tps=True,
        width=60,
    ) is None
    assert resolve_status_bar_throughput_label(
        {"last_call_tps": 40.0},
        show_tps=False,
        width=120,
    ) is None


def test_should_show_status_bar_tps():
    assert should_show_status_bar_tps(True) is True
    assert should_show_status_bar_tps(False) is False


def test_format_status_bar_tps_rejects_nan():
    assert format_status_bar_tps(float("nan")) is None


def test_live_throughput_snapshot_prefers_agent_over_cli():
    agent = SimpleNamespace(
        _stream_gen_started_at=1000.0,
        _stream_gen_tokens_est=200,
        _last_call_tps=55.0,
    )
    snap = live_throughput_snapshot(
        agent,
        cli_started_at=500.0,
        cli_tokens_est=10,
        cli_last_call_tps=9.0,
        now=1002.0,
    )
    assert snap["stream_tps"] == 100.0
    assert snap["last_call_tps"] == 55.0
