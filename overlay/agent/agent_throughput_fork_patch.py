"""Wire agent stream throughput tracking without Tier A edits.

Patches (via ``apply_agent_throughput_fork_patch``):

- ``AIAgent.__init__`` — sets ``compressor._fork_throughput_agent`` on the instance
  (no global agent registry).
- ``AIAgent._fire_stream_delta`` — ``record_agent_stream_delta``; failures logged.
- ``ContextCompressor.update_from_response`` — ``finalize_agent_call_tps`` using
  ``completion_tokens`` / ``output_tokens`` from usage; failures logged.

Idempotent: guarded by ``AIAgent._fork_throughput_patch_applied`` and per-wrap flags.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

_COMPRESSOR_AGENT_ATTR = "_fork_throughput_agent"


def _link_compressor_to_agent(agent: Any) -> None:
    compressor = getattr(agent, "context_compressor", None)
    if compressor is not None:
        setattr(compressor, _COMPRESSOR_AGENT_ATTR, agent)


def _completion_tokens_from_usage(usage: Dict[str, Any]) -> int:
    for key in ("completion_tokens", "output_tokens"):
        raw = usage.get(key)
        if raw is not None:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return 0


def apply_agent_throughput_fork_patch() -> None:
    from agent.context_compressor import ContextCompressor
    from hermes_cli.status_bar_throughput import (
        finalize_agent_call_tps,
        record_agent_stream_delta,
    )
    from run_agent import AIAgent

    if getattr(AIAgent, "_fork_throughput_patch_applied", False):
        return

    if not getattr(AIAgent, "_fork_throughput_init_wrapped", False):
        _orig_init = AIAgent.__init__

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _orig_init(self, *args, **kwargs)
            _link_compressor_to_agent(self)

        AIAgent.__init__ = __init__  # type: ignore[method-assign]
        AIAgent._fork_throughput_init_wrapped = True

    _orig_fire = AIAgent._fire_stream_delta

    def _fire_stream_delta(self, text: str) -> None:
        if isinstance(text, str) and text:
            try:
                record_agent_stream_delta(self, text)
            except Exception:
                logger.debug("record_agent_stream_delta failed", exc_info=True)
        return _orig_fire(self, text)

    AIAgent._fire_stream_delta = _fire_stream_delta  # type: ignore[method-assign]

    if not getattr(ContextCompressor, "_fork_throughput_update_wrapped", False):
        _orig_update = ContextCompressor.update_from_response

        def update_from_response(self, usage: Dict[str, Any]) -> None:
            _orig_update(self, usage)
            agent = getattr(self, _COMPRESSOR_AGENT_ATTR, None)
            if agent is None:
                return
            try:
                completion = _completion_tokens_from_usage(usage or {})
                finalize_agent_call_tps(
                    agent,
                    completion_tokens=completion,
                    api_duration=0.0,
                )
            except Exception:
                logger.debug("finalize_agent_call_tps failed", exc_info=True)

        ContextCompressor.update_from_response = update_from_response  # type: ignore[method-assign]
        ContextCompressor._fork_throughput_update_wrapped = True

    AIAgent._fork_throughput_patch_applied = True
