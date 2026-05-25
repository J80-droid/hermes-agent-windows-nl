"""Fork-owned session usage snapshot for TUI cost bar (upstream-safe extension).

Builds the gateway usage payload from agent session counters without patching
``agent.usage_pricing.estimate_usage_cost``.  If upstream later adds native
breakdown fields on the agent, this module preserves them and only fills gaps.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional


_ONE_MILLION = Decimal("1000000")


def _agent_get(agent: Any, key: str, fallback: Optional[str] = None) -> int:
    value = getattr(agent, key, 0) or (getattr(agent, fallback, 0) if fallback else 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _base_usage(agent: Any) -> dict[str, Any]:
    usage: dict[str, Any] = {
        "model": getattr(agent, "model", "") or "",
        "input": _agent_get(agent, "session_input_tokens", "session_prompt_tokens"),
        "output": _agent_get(agent, "session_output_tokens", "session_completion_tokens"),
        "cache_read": _agent_get(agent, "session_cache_read_tokens"),
        "cache_write": _agent_get(agent, "session_cache_write_tokens"),
        "reasoning": _agent_get(agent, "session_reasoning_tokens"),
        "prompt": _agent_get(agent, "session_prompt_tokens"),
        "completion": _agent_get(agent, "session_completion_tokens"),
        "total": _agent_get(agent, "session_total_tokens"),
        "calls": _agent_get(agent, "session_api_calls"),
    }

    comp = getattr(agent, "context_compressor", None)
    if comp:
        ctx_used = getattr(comp, "last_prompt_tokens", 0) or usage["total"] or 0
        ctx_max = getattr(comp, "context_length", 0) or 0
        if ctx_max:
            usage["context_used"] = ctx_used
            usage["context_max"] = ctx_max
            usage["context_percent"] = max(0, min(100, round(ctx_used / ctx_max * 100)))
        usage["compressions"] = getattr(comp, "compression_count", 0) or 0

    return usage


def _compute_cost_breakdown_usd(
    entry: Any,
    usage: Any,
) -> Optional[dict[str, float]]:
    if entry is None:
        return None

    parts: dict[str, float] = {
        "input": 0.0,
        "output": 0.0,
        "cache_read": 0.0,
        "cache_write": 0.0,
    }

    if entry.input_cost_per_million is not None and usage.input_tokens:
        parts["input"] = float(
            Decimal(usage.input_tokens) * entry.input_cost_per_million / _ONE_MILLION
        )
    if entry.output_cost_per_million is not None and usage.output_tokens:
        parts["output"] = float(
            Decimal(usage.output_tokens) * entry.output_cost_per_million / _ONE_MILLION
        )
    if entry.cache_read_cost_per_million is not None and usage.cache_read_tokens:
        parts["cache_read"] = float(
            Decimal(usage.cache_read_tokens)
            * entry.cache_read_cost_per_million
            / _ONE_MILLION
        )
    if entry.cache_write_cost_per_million is not None and usage.cache_write_tokens:
        parts["cache_write"] = float(
            Decimal(usage.cache_write_tokens)
            * entry.cache_write_cost_per_million
            / _ONE_MILLION
        )

    if sum(parts.values()) <= 0:
        return None

    return parts


def _compute_cost_breakdown_pct(breakdown_usd: dict[str, float]) -> Optional[dict[str, int]]:
    total = sum(breakdown_usd.values())
    if total <= 0:
        return None

    keys = (
        ("in", breakdown_usd["input"]),
        ("out", breakdown_usd["output"]),
        ("cr", breakdown_usd["cache_read"]),
        ("cw", breakdown_usd["cache_write"]),
    )
    shares = [(key, (value / total) * 100) for key, value in keys if value > 0]
    if not shares:
        return None

    pct: dict[str, int] = {key: int(share) for key, share in shares}
    remainders = sorted(
        ((share - int(share), key) for key, share in shares),
        reverse=True,
    )
    deficit = 100 - sum(pct.values())
    for index in range(deficit):
        pct[remainders[index % len(remainders)][1]] += 1

    return pct


def _seed_agent_session_cost(agent: Any, usage: dict[str, Any]) -> None:
    """Prefer per-call accumulated session cost when the agent already tracked it."""
    status = getattr(agent, "session_cost_status", None)
    if status not in {"estimated", "actual", "included"}:
        return
    cost = getattr(agent, "session_estimated_cost_usd", None)
    if cost is None:
        return
    try:
        usage["cost_usd"] = float(cost)
    except (TypeError, ValueError):
        return
    usage["cost_status"] = status


def _attach_cost_fields(agent: Any, usage: dict[str, Any]) -> None:
    """Add cost_usd, cost_status, and optional breakdown fields."""
    if (
        usage.get("cost_usd") is not None
        and usage.get("cost_breakdown_usd")
        and usage.get("cost_status") is not None
    ):
        return

    try:
        from agent.usage_pricing import CanonicalUsage, estimate_usage_cost, get_pricing_entry
    except ImportError:
        return

    canonical = CanonicalUsage(
        input_tokens=int(usage.get("input") or 0),
        output_tokens=int(usage.get("output") or 0),
        cache_read_tokens=int(usage.get("cache_read") or 0),
        cache_write_tokens=int(usage.get("cache_write") or 0),
    )

    provider = getattr(agent, "provider", None)
    base_url = getattr(agent, "base_url", None)
    model = str(usage.get("model") or "")

    if usage.get("cost_usd") is None:
        cost = estimate_usage_cost(
            model,
            canonical,
            provider=provider,
            base_url=base_url,
        )
        usage["cost_status"] = cost.status
        if cost.amount_usd is not None:
            usage["cost_usd"] = float(cost.amount_usd)
    elif "cost_status" not in usage:
        cost = estimate_usage_cost(
            model,
            canonical,
            provider=provider,
            base_url=base_url,
        )
        usage["cost_status"] = cost.status

    if usage.get("cost_breakdown_usd") or usage.get("cost_status") in {"included", "unknown"}:
        return

    entry = get_pricing_entry(model, provider=provider, base_url=base_url)
    breakdown_usd = _compute_cost_breakdown_usd(entry, canonical)
    if breakdown_usd:
        usage["cost_breakdown_usd"] = breakdown_usd
        pct = _compute_cost_breakdown_pct(breakdown_usd)
        if pct:
            usage["cost_breakdown_pct"] = pct


def build_session_usage_snapshot(agent: Any) -> dict[str, Any]:
    """Build the TUI usage payload for the current agent session."""
    usage = _base_usage(agent)

    upstream_breakdown = getattr(agent, "cost_breakdown_usd", None)
    if isinstance(upstream_breakdown, dict):
        usage["cost_breakdown_usd"] = upstream_breakdown
    upstream_pct = getattr(agent, "cost_breakdown_pct", None)
    if isinstance(upstream_pct, dict):
        usage["cost_breakdown_pct"] = upstream_pct
    upstream_tools = getattr(agent, "session_tool_executions", None)
    if upstream_tools is not None:
        try:
            usage["session_tools_executed"] = int(upstream_tools or 0)
        except (TypeError, ValueError):
            pass

    _seed_agent_session_cost(agent, usage)
    _attach_cost_fields(agent, usage)

    try:
        from hermes_cli.status_bar_throughput import _coerce_finite_rate

        last_call_tps = _coerce_finite_rate(getattr(agent, "_last_call_tps", None))
        if last_call_tps is not None:
            usage["last_call_tps"] = last_call_tps
    except Exception:
        pass

    return usage
