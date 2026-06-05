"""Wire agent stream throughput tracking without Tier A edits."""
from __future__ import annotations

from typing import Any, Dict

_AGENT_BY_COMPRESSOR: dict[int, Any] = {}


def apply_agent_throughput_fork_patch() -> None:
    from agent.context_compressor import ContextCompressor
    from run_agent import AIAgent

    if getattr(AIAgent, "_fork_throughput_patch_applied", False):
        return

    if not getattr(AIAgent, "_fork_throughput_init_wrapped", False):
        _orig_init = AIAgent.__init__

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _orig_init(self, *args, **kwargs)
            compressor = getattr(self, "context_compressor", None)
            if compressor is not None:
                _AGENT_BY_COMPRESSOR[id(compressor)] = self

        AIAgent.__init__ = __init__  # type: ignore[method-assign]
        AIAgent._fork_throughput_init_wrapped = True

    _orig_fire = AIAgent._fire_stream_delta

    def _fire_stream_delta(self, text: str) -> None:
        if isinstance(text, str) and text:
            try:
                from hermes_cli.status_bar_throughput import record_agent_stream_delta

                record_agent_stream_delta(self, text)
            except Exception:
                pass
        return _orig_fire(self, text)

    AIAgent._fire_stream_delta = _fire_stream_delta  # type: ignore[method-assign]

    if not getattr(ContextCompressor, "_fork_throughput_update_wrapped", False):
        _orig_update = ContextCompressor.update_from_response

        def update_from_response(self, usage: Dict[str, Any]) -> None:
            _orig_update(self, usage)
            agent = _AGENT_BY_COMPRESSOR.get(id(self))
            if agent is None:
                return
            try:
                from hermes_cli.status_bar_throughput import finalize_agent_call_tps

                completion = int(
                    usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
                )
                finalize_agent_call_tps(agent, completion_tokens=completion, api_duration=0.0)
            except Exception:
                pass

        ContextCompressor.update_from_response = update_from_response  # type: ignore[method-assign]
        ContextCompressor._fork_throughput_update_wrapped = True

    AIAgent._fork_throughput_patch_applied = True
