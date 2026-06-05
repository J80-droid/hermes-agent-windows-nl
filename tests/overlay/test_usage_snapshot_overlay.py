"""Overlay usage_snapshot tests (gemini pricing via bootstrap patch)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from overlay.bootstrap import install

install()

from hermes_cli.usage_snapshot import build_session_usage_snapshot


def _gemini_agent():
    return SimpleNamespace(
        model="gemini-3.5-flash",
        provider="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        session_input_tokens=5000,
        session_output_tokens=500,
        session_cache_read_tokens=16000,
        session_cache_write_tokens=0,
        session_prompt_tokens=21000,
        session_completion_tokens=500,
        session_total_tokens=21500,
        session_api_calls=11,
        context_compressor=None,
    )


def test_gemini_usage_snapshot_has_estimated_cost():
    usage = build_session_usage_snapshot(_gemini_agent())
    assert usage.get("cost_status") == "estimated"
    assert usage.get("cost_usd") is not None
    assert float(usage["cost_usd"]) > 0
