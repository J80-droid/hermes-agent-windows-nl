"""Classic CLI + shared status-bar throughput formatting (parity with statusBarThroughput.ts)."""

from __future__ import annotations

import math
import time
from typing import Any, Mapping, Optional

MIN_ELAPSED_SEC = 0.5
MIN_TPS = 1.0
THROUGHPUT_MIN_WIDTH = 76


def _coerce_finite_rate(value: Any) -> Optional[float]:
    if not isinstance(value, (int, float)):
        return None
    rate = float(value)
    if not math.isfinite(rate) or rate < MIN_TPS:
        return None
    return rate


def compute_live_tps(
    tokens: int,
    started_at: Optional[float],
    now: Optional[float] = None,
    *,
    min_elapsed: float = MIN_ELAPSED_SEC,
) -> Optional[float]:
    if started_at is None or not isinstance(started_at, (int, float)):
        return None
    if not math.isfinite(float(started_at)) or tokens < 1:
        return None
    elapsed = (now if now is not None else time.time()) - float(started_at)
    if not math.isfinite(elapsed) or elapsed < min_elapsed:
        return None
    return _coerce_finite_rate(tokens / elapsed)


def compute_call_tps(
    completion_tokens: int,
    gen_seconds: float,
    *,
    min_elapsed: float = MIN_ELAPSED_SEC,
) -> Optional[float]:
    if completion_tokens < 1 or not math.isfinite(gen_seconds) or gen_seconds <= 0:
        return None
    elapsed = max(float(gen_seconds), min_elapsed)
    return _coerce_finite_rate(completion_tokens / elapsed)


def format_status_bar_tps(tps: Optional[float]) -> Optional[str]:
    rate = _coerce_finite_rate(tps)
    if rate is None:
        return None
    return f"{int(round(rate))} tok/s"


def should_show_status_bar_tps(show_tps: bool) -> bool:
    return show_tps


def reset_agent_stream_tps_live(agent: Any) -> None:
    agent._stream_gen_started_at = None
    agent._stream_gen_tokens_est = 0


def record_agent_stream_delta(agent: Any, text: str) -> None:
    if not text:
        return
    try:
        from agent.model_metadata import estimate_tokens_rough
    except ImportError:
        return
    if getattr(agent, "_stream_gen_started_at", None) is None:
        agent._stream_gen_started_at = time.time()
    delta_tokens = estimate_tokens_rough(text)
    if delta_tokens < 1:
        return
    agent._stream_gen_tokens_est = (
        int(getattr(agent, "_stream_gen_tokens_est", 0) or 0) + delta_tokens
    )


def live_throughput_snapshot(
    agent: Any = None,
    *,
    cli_started_at: Optional[float] = None,
    cli_tokens_est: int = 0,
    cli_last_call_tps: Optional[float] = None,
    now: Optional[float] = None,
) -> dict[str, Optional[float]]:
    """Build stream_tps / last_call_tps fields for the status-bar snapshot."""
    started_at = None
    tokens_est = 0
    if agent is not None:
        started_at = getattr(agent, "_stream_gen_started_at", None)
        tokens_est = int(getattr(agent, "_stream_gen_tokens_est", 0) or 0)
    if started_at is None and cli_started_at is not None:
        started_at = cli_started_at
        tokens_est = int(cli_tokens_est or 0)

    stream_tps = None
    if started_at is not None and tokens_est > 0:
        stream_tps = compute_live_tps(tokens_est, started_at, now=now)

    last_call_tps = None
    if agent is not None:
        last_call_tps = _coerce_finite_rate(getattr(agent, "_last_call_tps", None))
    if last_call_tps is None:
        last_call_tps = _coerce_finite_rate(cli_last_call_tps)

    return {"stream_tps": stream_tps, "last_call_tps": last_call_tps}


def finalize_agent_call_tps(
    agent: Any,
    completion_tokens: int,
    api_duration: float,
) -> None:
    started_at = getattr(agent, "_stream_gen_started_at", None)
    if started_at is not None:
        gen_seconds = max(0.0, time.time() - started_at)
    else:
        gen_seconds = max(0.0, float(api_duration or 0.0))

    tokens = int(completion_tokens or 0)
    if tokens < 1:
        tokens = int(getattr(agent, "_stream_gen_tokens_est", 0) or 0)

    frozen = compute_call_tps(tokens, gen_seconds)
    if frozen is not None:
        agent._last_call_tps = frozen
    reset_agent_stream_tps_live(agent)


def resolve_status_bar_throughput_label(
    snapshot: Mapping[str, Any],
    *,
    show_tps: bool,
    width: int = 120,
) -> Optional[str]:
    if not should_show_status_bar_tps(show_tps) or width < THROUGHPUT_MIN_WIDTH:
        return None

    label = format_status_bar_tps(_coerce_finite_rate(snapshot.get("stream_tps")))
    if label:
        return label

    return format_status_bar_tps(_coerce_finite_rate(snapshot.get("last_call_tps")))
