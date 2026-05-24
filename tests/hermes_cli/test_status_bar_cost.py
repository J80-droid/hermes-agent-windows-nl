"""Unit tests for hermes_cli.status_bar_cost (parity with usageCostBar.test.ts)."""

from hermes_cli.status_bar_cost import (
    format_cost_breakdown_pct,
    format_session_cost_label,
    format_status_bar_cost_rich,
    format_usd_compact,
    resolve_cost_bar_tier,
    resolve_status_bar_cost_label,
    should_show_status_bar_cost,
)

USAGE = {
    "calls": 7,
    "cost_breakdown_pct": {"cw": 43, "out": 40, "in": 16, "cr": 1},
    "cost_status": "estimated",
    "cost_usd": 5.74,
    "session_tools_executed": 12,
    "turn_cost_usd": 0.23,
}


def test_format_usd_compact():
    assert format_usd_compact(0.23) == "$0.23"
    assert format_usd_compact(5.74) == "$5.74"


def test_format_cost_breakdown_pct_orders_cw_out_in_cr():
    assert format_cost_breakdown_pct(USAGE["cost_breakdown_pct"]) == (
        "cw 43% │ out 40% │ in 16% │ cr 1%"
    )


def test_format_status_bar_cost_rich_full_tier():
    text = format_status_bar_cost_rich(USAGE, mode="rich", width=120)
    assert "$0.23 / $5.74" in text
    assert "cw 43%" in text
    assert "7 calls" in text
    assert "12 tools" in text
    assert "~$5.74" not in text


def test_format_status_bar_cost_rich_turn_tilde_when_estimated():
    text = format_status_bar_cost_rich(
        {**USAGE, "turn_cost_estimated": True, "turn_cost_usd": 0.05},
        mode="rich",
        width=120,
    )
    assert "~$0.05 / $5.74" in text


def test_format_status_bar_cost_rich_costs_tier():
    assert format_status_bar_cost_rich(USAGE, mode="rich", width=70) == (
        "$0.23 / $5.74 │ 7 calls │ 12 tools"
    )


def test_format_status_bar_cost_rich_session_tier():
    assert format_status_bar_cost_rich(USAGE, mode="rich", width=40) == "$5.74"


def test_format_status_bar_cost_rich_minimal_mode():
    assert format_status_bar_cost_rich(USAGE, mode="minimal", width=120) == "~$5.7400"


def test_format_session_cost_label_fallbacks():
    assert format_session_cost_label({"cost_status": "unknown", "calls": 3}) == "n/a"
    assert format_session_cost_label({"cost_status": "included", "calls": 3}) == "included"
    assert format_session_cost_label({"calls": 0}) == "$0.00"


def test_format_status_bar_cost_rich_live_tokens_when_usd_unknown():
    text = format_status_bar_cost_rich(
        {
            "calls": 2,
            "cost_status": "unknown",
            "turn_cost_estimated": True,
            "turn_live_tokens": 1200,
        },
        mode="rich",
        width=120,
    )
    assert "~1.2K tok / n/a" in text


def test_should_show_status_bar_cost():
    assert should_show_status_bar_cost(True) is True
    assert should_show_status_bar_cost(False) is False


def test_resolve_cost_bar_tier():
    assert resolve_cost_bar_tier(120, "rich") == "full"
    assert resolve_cost_bar_tier(72, "rich") == "full"
    assert resolve_cost_bar_tier(70, "rich") == "costs"
    assert resolve_cost_bar_tier(40, "minimal") == "session"


def test_resolve_status_bar_cost_label_respects_show_cost():
    assert resolve_status_bar_cost_label(USAGE, show_cost=False, width=120) is None
    assert resolve_status_bar_cost_label(USAGE, show_cost=True, width=120) == (
        format_status_bar_cost_rich(USAGE, mode="rich", width=120)
    )
