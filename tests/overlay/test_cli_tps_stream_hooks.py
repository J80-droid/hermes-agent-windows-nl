"""Unit tests for overlay CLI stream throughput hooks."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from overlay.hermes_cli.cli_tps_stream_hooks import freeze_stream_tps_segment, record_stream_tps_delta


def _cli(**overrides):
    base = dict(
        _stream_tps_started_at=None,
        _stream_tps_tokens_est=0,
        _last_call_tps=None,
        agent=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@patch("agent.model_metadata.estimate_tokens_rough", return_value=12)
def test_record_stream_tps_delta_accumulates(mock_est):
    cli = _cli()
    record_stream_tps_delta(cli, "hello world")
    assert cli._stream_tps_started_at is not None
    assert cli._stream_tps_tokens_est == 12


def test_record_stream_tps_delta_ignores_empty():
    cli = _cli()
    record_stream_tps_delta(cli, "")
    record_stream_tps_delta(cli, None)
    assert cli._stream_tps_started_at is None
    assert cli._stream_tps_tokens_est == 0


@patch("overlay.hermes_cli.cli_tps_stream_hooks.compute_live_tps", return_value=42.0)
def test_freeze_sets_last_call_tps_when_no_agent_tps(mock_tps):
    cli = _cli(
        _stream_tps_started_at=time.time() - 2.0,
        _stream_tps_tokens_est=100,
    )
    freeze_stream_tps_segment(cli)
    assert cli._last_call_tps == 42.0
    assert cli._stream_tps_started_at is None
    assert cli._stream_tps_tokens_est == 0


@patch("overlay.hermes_cli.cli_tps_stream_hooks.compute_live_tps", return_value=99.0)
def test_freeze_does_not_overwrite_agent_tps(mock_tps):
    agent = SimpleNamespace(_last_call_tps=55.0)
    cli = _cli(
        _stream_tps_started_at=time.time() - 2.0,
        _stream_tps_tokens_est=100,
        agent=agent,
    )
    freeze_stream_tps_segment(cli)
    assert cli._last_call_tps is None


def test_freeze_noop_without_tokens():
    cli = _cli(_stream_tps_started_at=time.time())
    freeze_stream_tps_segment(cli)
    assert cli._last_call_tps is None
