#!/usr/bin/env python3
"""Smoke: tui_gateway._get_usage includes cost_usd when pricing returns amount."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch


def main() -> None:
    from agent.usage_pricing import CostResult
    from tui_gateway import server

    agent = SimpleNamespace(
        model="openai/gpt-4o-mini",
        provider="openai",
        base_url="https://api.openai.com/v1",
        session_input_tokens=1000,
        session_output_tokens=500,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_prompt_tokens=1000,
        session_completion_tokens=500,
        session_total_tokens=1500,
        session_api_calls=2,
        context_compressor=None,
    )
    cost = CostResult(
        amount_usd=Decimal("0.0042"),
        status="estimated",
        source="provider_models_api",
        label="e2e-smoke",
    )
    with patch("agent.usage_pricing.estimate_usage_cost", return_value=cost):
        usage = server._get_usage(agent)

    assert usage.get("cost_usd") == 0.0042, usage
    assert usage.get("cost_status") == "estimated", usage
    print("gateway usage smoke ok")


if __name__ == "__main__":
    main()
