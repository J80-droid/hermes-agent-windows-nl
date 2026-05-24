"""Tests for fork-owned usage snapshot builder."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.usage_pricing import CostResult, PricingEntry
from hermes_cli.usage_snapshot import build_session_usage_snapshot


def _agent(**overrides):
    base = dict(
        model="anthropic/claude-opus-4-7",
        provider="anthropic",
        base_url="https://api.anthropic.com",
        session_input_tokens=1000,
        session_output_tokens=500,
        session_cache_read_tokens=100,
        session_cache_write_tokens=200,
        session_prompt_tokens=1300,
        session_completion_tokens=500,
        session_total_tokens=1800,
        session_api_calls=7,
        context_compressor=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_session_usage_snapshot_includes_base_counters():
    usage = build_session_usage_snapshot(_agent())
    assert usage["calls"] == 7
    assert usage["input"] == 1000
    assert usage["output"] == 500
    assert usage["cache_read"] == 100
    assert usage["cache_write"] == 200


def test_build_session_usage_snapshot_includes_cost_and_breakdown():
    entry = PricingEntry(
        input_cost_per_million=Decimal("5"),
        output_cost_per_million=Decimal("25"),
        cache_read_cost_per_million=Decimal("0.5"),
        cache_write_cost_per_million=Decimal("6.25"),
        source="official_docs_snapshot",
    )
    cost = CostResult(
        amount_usd=Decimal("0.023"),
        status="estimated",
        source="official_docs_snapshot",
        label="test",
    )

    with patch("agent.usage_pricing.estimate_usage_cost", return_value=cost), patch(
        "agent.usage_pricing.get_pricing_entry", return_value=entry
    ):
        usage = build_session_usage_snapshot(_agent())

    assert usage["cost_usd"] == pytest.approx(0.023)
    assert usage["cost_status"] == "estimated"
    assert "cost_breakdown_usd" in usage
    assert "cost_breakdown_pct" in usage
    pct = usage["cost_breakdown_pct"]
    assert sum(pct.values()) == 100


def test_build_session_usage_snapshot_skips_breakdown_when_included():
    cost = CostResult(
        amount_usd=Decimal("0"),
        status="included",
        source="none",
        label="included",
        pricing_version="included-route",
    )

    with patch("agent.usage_pricing.estimate_usage_cost", return_value=cost):
        usage = build_session_usage_snapshot(_agent())

    assert usage["cost_status"] == "included"
    assert "cost_breakdown_usd" not in usage
    assert "cost_breakdown_pct" not in usage


def test_build_session_usage_snapshot_preserves_upstream_breakdown():
    agent = _agent(
        cost_breakdown_usd={"input": 1.0, "output": 2.0, "cache_read": 0.1, "cache_write": 0.9},
        cost_breakdown_pct={"in": 25, "out": 50, "cr": 3, "cw": 22},
        session_tool_executions=12,
    )
    cost = CostResult(
        amount_usd=Decimal("4.0"),
        status="estimated",
        source="provider_models_api",
        label="test",
    )

    with patch("agent.usage_pricing.estimate_usage_cost", return_value=cost):
        usage = build_session_usage_snapshot(agent)

    assert usage["cost_breakdown_usd"]["output"] == 2.0
    assert usage["cost_breakdown_pct"]["out"] == 50
    assert usage["session_tools_executed"] == 12


def test_build_session_usage_snapshot_gemini_35_flash_cache_no_unknown():
    """Integration: real Google catalog, no mocks — cache hits must not yield n/a."""
    agent = _agent(
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
    )
    usage = build_session_usage_snapshot(agent)
    assert usage["cost_status"] == "estimated"
    assert usage["cost_usd"] == pytest.approx(0.0144, abs=1e-6)
    assert "cost_breakdown_usd" in usage
    assert usage["cost_breakdown_usd"]["cache_read"] > 0


def test_build_session_usage_snapshot_prefers_agent_session_cost():
    agent = _agent(
        session_estimated_cost_usd=0.42,
        session_cost_status="estimated",
    )
    usage = build_session_usage_snapshot(agent)
    assert usage["cost_usd"] == pytest.approx(0.42)
    assert usage["cost_status"] == "estimated"
