"""Classic CLI stream throughput hooks (overlay; Tier A cli.py unchanged)."""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from hermes_cli.status_bar_throughput import MIN_ELAPSED_SEC, compute_live_tps

logger = logging.getLogger(__name__)


def record_stream_tps_delta(self: Any, text: Optional[str]) -> None:
    """Track estimated tokens for live tok/s on the CLI status bar."""
    if not text or not isinstance(text, str):
        return
    try:
        from agent.model_metadata import estimate_tokens_rough
    except ImportError:
        return

    if getattr(self, "_stream_tps_started_at", None) is None:
        self._stream_tps_started_at = time.time()
    delta = estimate_tokens_rough(text)
    if delta < 1:
        return
    self._stream_tps_tokens_est = int(getattr(self, "_stream_tps_tokens_est", 0) or 0) + delta

    agent = getattr(self, "agent", None)
    if agent is not None:
        try:
            from hermes_cli.status_bar_throughput import record_agent_stream_delta

            record_agent_stream_delta(agent, text)
        except Exception:
            logger.debug("record_agent_stream_delta from CLI stream failed", exc_info=True)


def freeze_stream_tps_segment(self: Any) -> None:
    """Freeze live CLI stream segment; never overwrite agent._last_call_tps."""
    started = getattr(self, "_stream_tps_started_at", None)
    tokens = int(getattr(self, "_stream_tps_tokens_est", 0) or 0)
    agent = getattr(self, "agent", None)
    agent_tps = getattr(agent, "_last_call_tps", None) if agent is not None else None

    if started is not None and tokens > 0:
        rate = compute_live_tps(tokens, started, min_elapsed=MIN_ELAPSED_SEC)
        if rate is not None and agent_tps is None:
            self._last_call_tps = rate

    self._stream_tps_started_at = None
    self._stream_tps_tokens_est = 0
