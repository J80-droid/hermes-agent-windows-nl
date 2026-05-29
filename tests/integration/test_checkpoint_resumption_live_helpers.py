"""Unit tests for live batch checkpoint opt-in helpers (no API calls)."""

from __future__ import annotations

import pytest

from tests.integration import test_checkpoint_resumption as tcr


def test_live_batch_opt_in_false_by_default(monkeypatch):
    monkeypatch.delenv("HERMES_RUN_LIVE_BATCH", raising=False)
    assert tcr._live_batch_opt_in() is False


def test_live_batch_opt_in_accepts_truthy_values(monkeypatch):
    monkeypatch.setenv("HERMES_RUN_LIVE_BATCH", "yes")
    assert tcr._live_batch_opt_in() is True


def test_live_batch_runner_kwargs_none_without_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_RUN_LIVE_BATCH", "1")
    monkeypatch.setenv("HERMES_LIVE_TEST_HOME", str(tmp_path))
    assert tcr.live_batch_runner_kwargs(monkeypatch) is None
