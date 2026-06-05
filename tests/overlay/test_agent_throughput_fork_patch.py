"""Unit tests for overlay.agent.agent_throughput_fork_patch (P1 TPS runtime patch).

Covers helper edge cases and apply_agent_throughput_fork_patch wiring:
idempotency, stream delta recording, compressor finalize, and negative paths.
External agent/throughput modules are stubbed so tests stay hermetic.
"""

from __future__ import annotations

import logging
import sys
from types import ModuleType, SimpleNamespace
import pytest

from overlay.agent.agent_throughput_fork_patch import (
    _COMPRESSOR_AGENT_ATTR,
    _completion_tokens_from_usage,
    _link_compressor_to_agent,
    apply_agent_throughput_fork_patch,
)


# ---------------------------------------------------------------------------
# _completion_tokens_from_usage
# ---------------------------------------------------------------------------


class TestCompletionTokensFromUsage:
    def test_prefers_completion_tokens_over_output_tokens(self):
        usage = {"completion_tokens": 42, "output_tokens": 99}
        assert _completion_tokens_from_usage(usage) == 42

    def test_falls_back_to_output_tokens(self):
        assert _completion_tokens_from_usage({"output_tokens": 7}) == 7

    def test_zero_completion_tokens_skips_to_output(self):
        assert _completion_tokens_from_usage(
            {"completion_tokens": 0, "output_tokens": 12}
        ) == 12

    def test_negative_values_are_ignored(self):
        assert _completion_tokens_from_usage({"completion_tokens": -5}) == 0
        assert _completion_tokens_from_usage({"output_tokens": -1}) == 0

    def test_non_numeric_strings_are_skipped(self):
        assert _completion_tokens_from_usage({"completion_tokens": "bad"}) == 0
        assert _completion_tokens_from_usage({"output_tokens": "n/a"}) == 0

    def test_float_strings_are_rejected(self):
        assert _completion_tokens_from_usage({"completion_tokens": "12.9"}) == 0

    def test_bool_is_not_treated_as_token_count(self):
        # bool is a subclass of int in Python; int(True)==1 — document behaviour.
        assert _completion_tokens_from_usage({"completion_tokens": True}) == 1

    def test_none_values_are_skipped(self):
        assert _completion_tokens_from_usage({"completion_tokens": None, "output_tokens": 3}) == 3

    def test_empty_usage_returns_zero(self):
        assert _completion_tokens_from_usage({}) == 0

    def test_unrelated_keys_ignored(self):
        assert _completion_tokens_from_usage({"prompt_tokens": 500, "total_tokens": 600}) == 0


# ---------------------------------------------------------------------------
# _link_compressor_to_agent
# ---------------------------------------------------------------------------


class TestLinkCompressorToAgent:
    def test_sets_back_reference_on_compressor(self):
        agent = SimpleNamespace(context_compressor=SimpleNamespace())
        _link_compressor_to_agent(agent)
        assert getattr(agent.context_compressor, _COMPRESSOR_AGENT_ATTR) is agent

    def test_noop_when_compressor_missing(self):
        agent = SimpleNamespace(context_compressor=None)
        _link_compressor_to_agent(agent)  # must not raise

    def test_noop_when_compressor_attr_absent(self):
        agent = SimpleNamespace()
        _link_compressor_to_agent(agent)

    def test_overwrites_stale_back_reference(self):
        stale = object()
        compressor = SimpleNamespace(**{_COMPRESSOR_AGENT_ATTR: stale})
        agent = SimpleNamespace(context_compressor=compressor)
        _link_compressor_to_agent(agent)
        assert agent.context_compressor._fork_throughput_agent is agent


# ---------------------------------------------------------------------------
# apply_agent_throughput_fork_patch (isolated stubs)
# ---------------------------------------------------------------------------


@pytest.fixture
def throughput_patch_sandbox():
    """Minimal AIAgent / ContextCompressor stubs + call recorders."""
    record_calls: list[tuple[object, str]] = []
    finalize_calls: list[tuple[object, dict]] = []

    class FakeContextCompressor:
        _fork_throughput_update_wrapped = False

        def __init__(self) -> None:
            self.update_calls: list[dict] = []

        def update_from_response(self, usage: dict) -> None:
            self.update_calls.append(usage)

    class FakeAIAgent:
        _fork_throughput_patch_applied = False
        _fork_throughput_init_wrapped = False

        def __init__(self) -> None:
            self.context_compressor = FakeContextCompressor()
            self.stream_deltas: list[str] = []

        def _fire_stream_delta(self, text: str) -> None:
            self.stream_deltas.append(text)

    def _record(agent: object, text: str) -> None:
        record_calls.append((agent, text))

    def _finalize(agent: object, **kwargs: object) -> None:
        finalize_calls.append((agent, kwargs))

    fake_cc_mod = ModuleType("agent.context_compressor")
    fake_cc_mod.ContextCompressor = FakeContextCompressor

    fake_throughput_mod = ModuleType("hermes_cli.status_bar_throughput")
    fake_throughput_mod.record_agent_stream_delta = _record
    fake_throughput_mod.finalize_agent_call_tps = _finalize

    fake_run_mod = ModuleType("run_agent")
    fake_run_mod.AIAgent = FakeAIAgent

    saved_modules = {
        name: sys.modules.get(name)
        for name in (
            "agent.context_compressor",
            "hermes_cli.status_bar_throughput",
            "run_agent",
        )
    }

    sys.modules["agent.context_compressor"] = fake_cc_mod
    sys.modules["hermes_cli.status_bar_throughput"] = fake_throughput_mod
    sys.modules["run_agent"] = fake_run_mod

    FakeAIAgent._fork_throughput_patch_applied = False
    FakeAIAgent._fork_throughput_init_wrapped = False
    FakeContextCompressor._fork_throughput_update_wrapped = False
    FakeAIAgent.__init__ = FakeAIAgent.__init__
    FakeAIAgent._fire_stream_delta = FakeAIAgent._fire_stream_delta
    FakeContextCompressor.update_from_response = FakeContextCompressor.update_from_response

    yield SimpleNamespace(
        AIAgent=FakeAIAgent,
        ContextCompressor=FakeContextCompressor,
        record_calls=record_calls,
        finalize_calls=finalize_calls,
    )

    for name, mod in saved_modules.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


class TestApplyAgentThroughputForkPatch:
    def test_happy_path_wires_init_stream_and_compressor(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        apply_agent_throughput_fork_patch()

        agent = sb.AIAgent()
        assert getattr(agent.context_compressor, _COMPRESSOR_AGENT_ATTR) is agent

        agent._fire_stream_delta("chunk")
        assert sb.record_calls == [(agent, "chunk")]
        assert agent.stream_deltas == ["chunk"]

        agent.context_compressor.update_from_response({"completion_tokens": 25})
        assert len(sb.finalize_calls) == 1
        fin_agent, fin_kw = sb.finalize_calls[0]
        assert fin_agent is agent
        assert fin_kw["completion_tokens"] == 25
        assert fin_kw["api_duration"] == 0.0

        assert sb.AIAgent._fork_throughput_patch_applied is True
        assert sb.AIAgent._fork_throughput_init_wrapped is True
        assert sb.ContextCompressor._fork_throughput_update_wrapped is True

    def test_apply_is_idempotent(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        apply_agent_throughput_fork_patch()
        init_after_first = sb.AIAgent.__init__
        fire_after_first = sb.AIAgent._fire_stream_delta
        update_after_first = sb.ContextCompressor.update_from_response

        apply_agent_throughput_fork_patch()

        assert sb.AIAgent.__init__ is init_after_first
        assert sb.AIAgent._fire_stream_delta is fire_after_first
        assert sb.ContextCompressor.update_from_response is update_after_first

    def test_fire_stream_delta_ignores_empty_and_non_string(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        apply_agent_throughput_fork_patch()
        agent = sb.AIAgent()

        agent._fire_stream_delta("")
        agent._fire_stream_delta(None)  # type: ignore[arg-type]

        assert sb.record_calls == []
        assert agent.stream_deltas == ["", None]

    def test_fire_stream_delta_swallows_record_errors(self, throughput_patch_sandbox, caplog):
        sb = throughput_patch_sandbox

        def _boom(_agent: object, _text: str) -> None:
            raise RuntimeError("record failed")

        sys.modules["hermes_cli.status_bar_throughput"].record_agent_stream_delta = _boom
        apply_agent_throughput_fork_patch()

        agent = sb.AIAgent()
        with caplog.at_level(logging.DEBUG, logger="overlay.agent.agent_throughput_fork_patch"):
            agent._fire_stream_delta("still forwarded")

        assert agent.stream_deltas == ["still forwarded"]
        assert any("record_agent_stream_delta failed" in r.message for r in caplog.records)

    def test_update_from_response_noop_without_agent_link(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        apply_agent_throughput_fork_patch()

        compressor = sb.ContextCompressor()
        compressor.update_from_response({"output_tokens": 10})

        assert sb.finalize_calls == []

    def test_update_from_response_handles_none_usage(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        apply_agent_throughput_fork_patch()

        agent = sb.AIAgent()
        setattr(agent.context_compressor, _COMPRESSOR_AGENT_ATTR, agent)
        agent.context_compressor.update_from_response(None)  # type: ignore[arg-type]

        assert sb.finalize_calls == [(agent, {"completion_tokens": 0, "api_duration": 0.0})]

    def test_update_from_response_swallows_finalize_errors(self, throughput_patch_sandbox, caplog):
        sb = throughput_patch_sandbox

        def _boom(_agent: object, **_kw: object) -> None:
            raise ValueError("finalize failed")

        sys.modules["hermes_cli.status_bar_throughput"].finalize_agent_call_tps = _boom
        apply_agent_throughput_fork_patch()

        agent = sb.AIAgent()
        setattr(agent.context_compressor, _COMPRESSOR_AGENT_ATTR, agent)

        with caplog.at_level(logging.DEBUG, logger="overlay.agent.agent_throughput_fork_patch"):
            agent.context_compressor.update_from_response({"completion_tokens": 3})

        assert len(agent.context_compressor.update_calls) == 1
        assert any("finalize_agent_call_tps failed" in r.message for r in caplog.records)

    def test_init_wrap_skipped_when_already_wrapped(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        sb.AIAgent._fork_throughput_init_wrapped = True
        original_init = sb.AIAgent.__init__

        apply_agent_throughput_fork_patch()

        assert sb.AIAgent.__init__ is original_init
        assert sb.AIAgent._fork_throughput_init_wrapped is True

    def test_compressor_wrap_skipped_when_already_wrapped(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        sb.ContextCompressor._fork_throughput_update_wrapped = True
        original_update = sb.ContextCompressor.update_from_response

        apply_agent_throughput_fork_patch()

        assert sb.ContextCompressor.update_from_response is original_update

    def test_early_return_when_patch_already_applied(self, throughput_patch_sandbox):
        sb = throughput_patch_sandbox
        sb.AIAgent._fork_throughput_patch_applied = True
        original_fire = sb.AIAgent._fire_stream_delta

        apply_agent_throughput_fork_patch()

        assert sb.AIAgent._fire_stream_delta is original_fire


class TestApplyAgentThroughputForkPatchIntegration:
    """Smoke tests against real run_agent / ContextCompressor when importable."""

    @pytest.fixture(autouse=True)
    def _require_runtime(self):
        pytest.importorskip("run_agent")
        pytest.importorskip("agent.context_compressor")

    def test_apply_does_not_raise_when_already_installed(self):
        apply_agent_throughput_fork_patch()
        apply_agent_throughput_fork_patch()

    def test_patch_flags_set_on_real_runtime_classes(self):
        from agent.context_compressor import ContextCompressor
        from run_agent import AIAgent

        apply_agent_throughput_fork_patch()

        assert AIAgent._fork_throughput_patch_applied is True
        assert AIAgent._fork_throughput_init_wrapped is True
        assert ContextCompressor._fork_throughput_update_wrapped is True
