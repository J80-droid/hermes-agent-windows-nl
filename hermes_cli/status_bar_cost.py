"""Classic CLI + shared status-bar cost formatting (parity with ui-tui usageCostBar.ts)."""

from __future__ import annotations

from typing import Any, Literal, Mapping, Optional

CostBarMode = Literal["minimal", "rich"]

FULL_MIN_WIDTH = 72
COSTS_MIN_WIDTH = 58


def format_usd_compact(amount: float) -> str:
    return f"${amount:.2f}"


def format_session_cost_label(usage: Mapping[str, Any]) -> str:
    cost_usd = usage.get("cost_usd")
    if isinstance(cost_usd, (int, float)):
        return format_usd_compact(float(cost_usd))

    cost_status = usage.get("cost_status")
    if cost_status == "included":
        return "included"
    if cost_status == "unknown":
        return "n/a"

    calls = usage.get("calls") or 0
    if not calls:
        return "$0.00"

    return "n/a"


def format_status_bar_cost_minimal(usage: Mapping[str, Any]) -> str:
    cost_usd = usage.get("cost_usd")
    if not isinstance(cost_usd, (int, float)):
        return format_session_cost_label(usage)

    prefix = "~" if usage.get("cost_status") == "estimated" else ""
    return f"{prefix}${float(cost_usd):.4f}"


def format_turn_cost_label(usage: Mapping[str, Any]) -> Optional[str]:
    turn_cost = usage.get("turn_cost_usd")
    if isinstance(turn_cost, (int, float)) and turn_cost > 0:
        prefix = "~" if usage.get("turn_cost_estimated") else ""
        return f"{prefix}${float(turn_cost):.2f}"

    live_tokens = usage.get("turn_live_tokens")
    if isinstance(live_tokens, (int, float)) and live_tokens > 0:
        tokens = int(live_tokens)
        if tokens >= 1_000_000:
            label = f"{tokens / 1_000_000:.1f}M".replace(".0M", "M")
        elif tokens >= 1_000:
            label = f"{tokens / 1_000:.1f}K".replace(".0K", "K")
        else:
            label = str(tokens)
        return f"~{label} tok"

    return None


def format_cost_breakdown_pct(pct: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not pct:
        return None

    parts: list[str] = []
    for key, label in (("cw", "cw"), ("out", "out"), ("in", "in"), ("cr", "cr")):
        value = pct.get(key)
        if isinstance(value, (int, float)):
            parts.append(f"{label} {int(value)}%")

    return " │ ".join(parts) if parts else None


def resolve_cost_bar_tier(width: int, mode: CostBarMode) -> Literal["costs", "full", "session"]:
    if mode != "rich":
        return "session"
    if width >= FULL_MIN_WIDTH:
        return "full"
    if width >= COSTS_MIN_WIDTH:
        return "costs"
    return "session"


def format_status_bar_cost_rich(
    usage: Mapping[str, Any],
    *,
    mode: CostBarMode = "rich",
    width: int = FULL_MIN_WIDTH,
) -> str:
    if mode == "minimal":
        return format_status_bar_cost_minimal(usage)

    session = format_session_cost_label(usage)
    turn = format_turn_cost_label(usage)
    tier = resolve_cost_bar_tier(width, mode)

    if tier == "session":
        return session

    cost_pair = f"{turn} / {session}" if turn else session
    calls = usage.get("calls") or 0
    tools = usage.get("session_tools_executed") or 0
    call_label = f"{calls} calls" if calls else None
    tools_label = f"{tools} tools" if tools else None

    if tier == "costs":
        tail = " │ ".join(part for part in (call_label, tools_label) if part)
        return f"{cost_pair} │ {tail}" if tail else cost_pair

    breakdown = format_cost_breakdown_pct(usage.get("cost_breakdown_pct"))
    segments = [part for part in (cost_pair, breakdown, call_label, tools_label) if part]
    return " │ ".join(segments)


def should_show_status_bar_cost(show_cost: bool) -> bool:
    return show_cost


def resolve_status_bar_cost_label(
    usage: Mapping[str, Any],
    *,
    show_cost: bool,
    cost_bar_mode: CostBarMode = "rich",
    width: int = FULL_MIN_WIDTH,
) -> Optional[str]:
    if not should_show_status_bar_cost(show_cost):
        return None
    return format_status_bar_cost_rich(usage, mode=cost_bar_mode, width=width)
