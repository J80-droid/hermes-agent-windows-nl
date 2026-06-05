"""Unit tests for overlay.hermes_cli.cli_fork_patch (status-bar runtime patch).

Focus: patch idempotency, display attrs, snapshot edge cases, cost/throughput
wiring, and negative paths. External providers and process_registry are mocked.
"""

from __future__ import annotations

import queue
from datetime import datetime, timedelta
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from overlay.bootstrap import install
from overlay.hermes_cli.cli_fork_patch import (
    CliForkStatusBarMixin,
    PATCH_METHOD_NAMES,
    apply_cli_fork_patch,
    apply_fork_display_attrs,
)

install()


def _make_cli(model: str = "anthropic/claude-sonnet-4-20250514"):
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.model = model
    cli.session_start = datetime.now() - timedelta(minutes=3)
    cli.conversation_history = []
    cli.agent = None
    cli._show_cost = True
    cli._show_status_bar_tps = True
    cli._show_prompt_timer_emoji = False
    cli._cost_bar_mode = "rich"
    cli._last_call_tps = None
    cli._stream_tps_started_at = None
    cli._stream_tps_tokens_est = 0
    cli._status_bar_visible = True
    cli._status_bar_layout_lines = 1
    cli._model_picker_state = None
    cli._pending_input = queue.Queue()
    cli._prompt_start_time = None
    cli._prompt_duration = 0.0
    cli.provider = None
    cli.base_url = None
    cli.api_key = None
    cli.session_id = "test-session"
    return cli


def _attach_agent(cli, **overrides):
    base = dict(
        model=cli.model,
        provider="anthropic",
        base_url="https://api.anthropic.com",
        api_key="fake",
        session_input_tokens=1000,
        session_output_tokens=200,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_prompt_tokens=1000,
        session_completion_tokens=200,
        session_total_tokens=1200,
        session_api_calls=3,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=5000,
            context_length=200_000,
            compression_count=0,
        ),
    )
    base.update(overrides)
    cli.agent = SimpleNamespace(**base)
    return cli


class TestApplyCliForkPatch:
    def test_patch_is_idempotent(self):
        from cli import HermesCLI

        apply_cli_fork_patch()
        init_after_first = HermesCLI.__init__
        wrapped_flag = getattr(HermesCLI, "_fork_display_init_wrapped", False)
        apply_cli_fork_patch()
        assert HermesCLI.__init__ is init_after_first
        assert getattr(HermesCLI, "_fork_status_bar_patch_applied") is True
        assert getattr(HermesCLI, "_fork_display_init_wrapped") is wrapped_flag

    def test_all_patch_method_names_bound_on_hermes_cli(self):
        from cli import HermesCLI

        for name in PATCH_METHOD_NAMES:
            assert hasattr(HermesCLI, name)
            assert getattr(HermesCLI, name) is getattr(CliForkStatusBarMixin, name)

    def test_pending_queue_helpers_attached(self):
        from cli import HermesCLI

        assert hasattr(HermesCLI, "_append_pending_queue_status_part")
        assert hasattr(HermesCLI, "_append_pending_queue_status_fragments")


class TestApplyForkDisplayAttrs:
    def test_applies_defaults_from_display_config(self):
        cli = _make_cli()
        fake_cli_mod = ModuleType("cli")
        fake_cli_mod.CLI_CONFIG = {
            "display": {
                "show_cost": True,
                "show_status_bar_tps": True,
                "show_prompt_timer_emoji": False,
                "cost_bar_mode": "rich",
            }
        }
        fake_cli_mod.is_truthy_value = lambda v: bool(v)

        with patch.dict("sys.modules", {"cli": fake_cli_mod}):
            apply_fork_display_attrs(cli)

        assert cli._show_cost is True
        assert cli._show_status_bar_tps is True
        assert cli._show_prompt_timer_emoji is False
        assert cli._cost_bar_mode == "rich"
        assert cli._status_bar_layout_lines == 1

    def test_invalid_cost_bar_mode_falls_back_to_rich(self):
        cli = _make_cli()
        fake_cli_mod = ModuleType("cli")
        fake_cli_mod.CLI_CONFIG = {"display": {"cost_bar_mode": "bogus"}}
        fake_cli_mod.is_truthy_value = lambda v: bool(v)

        with patch.dict("sys.modules", {"cli": fake_cli_mod}):
            apply_fork_display_attrs(cli)

        assert cli._cost_bar_mode == "rich"

    def test_show_cost_false_when_explicitly_disabled(self):
        cli = _make_cli()
        fake_cli_mod = ModuleType("cli")
        fake_cli_mod.CLI_CONFIG = {"display": {"show_cost": False}}
        fake_cli_mod.is_truthy_value = lambda v: bool(v)

        with patch.dict("sys.modules", {"cli": fake_cli_mod}):
            apply_fork_display_attrs(cli)

        assert cli._show_cost is False

    def test_import_error_is_silent(self):
        cli = _make_cli()
        with patch.dict("sys.modules", {"cli": None}):
            apply_fork_display_attrs(cli)  # must not raise


class TestStatusBarCostFormatWidth:
    def test_narrow_terminal_uses_minimum(self):
        cli = _make_cli()
        assert cli._status_bar_cost_format_width(60) == 40

    def test_wide_terminal_reserves_margin(self):
        cli = _make_cli()
        assert cli._status_bar_cost_format_width(120) == 88


class TestResolveStatusBarCostLabel:
    def test_returns_none_when_show_cost_disabled(self):
        cli = _attach_agent(_make_cli())
        cli._show_cost = False
        snap = cli._get_status_bar_snapshot()
        assert cli._resolve_status_bar_cost_label(snap, 120) is None

    def test_returns_none_when_terminal_too_narrow(self):
        cli = _attach_agent(_make_cli())
        snap = cli._get_status_bar_snapshot()
        assert cli._resolve_status_bar_cost_label(snap, 40) is None

    def test_returns_label_when_enabled_and_wide(self):
        cli = _attach_agent(_make_cli())
        snap = cli._get_status_bar_snapshot()
        label = cli._resolve_status_bar_cost_label(snap, 120)
        assert label is not None
        assert "$" in label or "included" in label.lower() or "n/a" in label.lower()

    def test_swallows_resolver_exception(self):
        cli = _attach_agent(_make_cli())
        snap = {"usage": {"calls": 1}}
        with patch(
            "hermes_cli.status_bar_cost.resolve_status_bar_cost_label",
            side_effect=RuntimeError("boom"),
        ):
            assert cli._resolve_status_bar_cost_label(snap, 120) is None


class TestGetStatusBarSnapshot:
    def test_without_agent_minimal_usage(self):
        cli = _make_cli()
        snap = cli._get_status_bar_snapshot()
        assert snap["usage"] == {"calls": 0}
        assert snap["session_api_calls"] == 0
        assert snap["context_percent"] is None

    def test_prefers_agent_model_over_stale_cli_model(self):
        cli = _make_cli(model="openrouter/old-model")
        cli.agent = SimpleNamespace(
            model="anthropic/claude-opus-4-7",
            provider="anthropic",
            base_url="",
            session_input_tokens=0,
            session_output_tokens=0,
            session_cache_read_tokens=0,
            session_cache_write_tokens=0,
            session_prompt_tokens=0,
            session_completion_tokens=0,
            session_total_tokens=0,
            session_api_calls=0,
            context_compressor=None,
        )
        snap = cli._get_status_bar_snapshot()
        assert snap["model_name"] == "anthropic/claude-opus-4-7"
        assert "claude-opus" in snap["model_short"]

    def test_truncates_long_model_short_name(self):
        cli = _make_cli(model="provider/" + ("x" * 40))
        cli.agent = SimpleNamespace(
            model=cli.model,
            provider="p",
            base_url="",
            session_input_tokens=0,
            session_output_tokens=0,
            session_cache_read_tokens=0,
            session_cache_write_tokens=0,
            session_prompt_tokens=0,
            session_completion_tokens=0,
            session_total_tokens=0,
            session_api_calls=0,
            context_compressor=None,
        )
        snap = cli._get_status_bar_snapshot()
        assert snap["model_short"].endswith("...")
        assert len(snap["model_short"]) <= 26

    def test_strips_gguf_suffix(self):
        cli = _make_cli(model="local/my-model.gguf")
        cli.agent = SimpleNamespace(
            model=cli.model,
            provider="ollama",
            base_url="",
            session_input_tokens=0,
            session_output_tokens=0,
            session_cache_read_tokens=0,
            session_cache_write_tokens=0,
            session_prompt_tokens=0,
            session_completion_tokens=0,
            session_total_tokens=0,
            session_api_calls=0,
            context_compressor=None,
        )
        snap = cli._get_status_bar_snapshot()
        assert not snap["model_short"].endswith(".gguf")

    def test_clamps_negative_context_tokens_after_compression(self):
        cli = _attach_agent(
            _make_cli(),
            context_compressor=SimpleNamespace(
                last_prompt_tokens=-1,
                context_length=200_000,
                compression_count=2,
            ),
        )
        snap = cli._get_status_bar_snapshot()
        assert snap["context_tokens"] == 0
        assert snap["compressions"] == 2
        assert snap["context_percent"] == 0

    def test_negative_context_length_treated_as_empty(self):
        cli = _attach_agent(
            _make_cli(),
            context_compressor=SimpleNamespace(
                last_prompt_tokens=100,
                context_length=-5,
                compression_count=0,
            ),
        )
        snap = cli._get_status_bar_snapshot()
        assert snap["context_length"] is None
        assert snap["context_percent"] is None

    def test_background_tasks_counted(self):
        cli = _attach_agent(_make_cli())
        cli._background_tasks = {"a": object(), "b": object()}
        snap = cli._get_status_bar_snapshot()
        assert snap["active_background_tasks"] == 2

    def test_background_tasks_read_failure_is_ignored(self):
        cli = _attach_agent(_make_cli())

        class _Broken:
            def __len__(self):
                raise OSError("broken")

        cli._background_tasks = _Broken()
        snap = cli._get_status_bar_snapshot()
        assert snap["active_background_tasks"] == 0

    def test_usage_snapshot_failure_falls_back_to_api_calls(self):
        cli = _attach_agent(_make_cli())
        with patch(
            "hermes_cli.usage_snapshot.build_session_usage_snapshot",
            side_effect=ValueError("no pricing"),
        ):
            snap = cli._get_status_bar_snapshot()
        assert snap["usage"]["calls"] == cli.agent.session_api_calls

    def test_throughput_failure_sets_none_fields(self):
        cli = _attach_agent(_make_cli())
        with patch(
            "hermes_cli.status_bar_throughput.live_throughput_snapshot",
            side_effect=ImportError("missing"),
        ):
            snap = cli._get_status_bar_snapshot()
        assert snap["stream_tps"] is None
        assert snap["last_call_tps"] is None

    def test_jatevo_quota_when_runtime_matches(self):
        cli = _attach_agent(
            _make_cli(),
            provider="jatevo",
            base_url="https://jatevo.ai/v1",
        )
        with (
            patch("agent.jatevo_usage.is_jatevo_runtime", return_value=True),
            patch("agent.jatevo_usage.resolve_status_bar_jatevo_quota", return_value=("JV 1/562", 0.2)),
            patch("agent.venice_usage.is_venice_runtime", return_value=False),
        ):
            snap = cli._get_status_bar_snapshot()
        assert snap["jatevo_quota_label"] == "JV 1/562"
        assert snap["jatevo_quota_percent"] == 0.2

    def test_provider_quota_exception_is_swallowed(self):
        cli = _attach_agent(_make_cli(), provider="jatevo", base_url="https://jatevo.ai/v1")
        with patch("agent.jatevo_usage.is_jatevo_runtime", side_effect=RuntimeError("x")):
            snap = cli._get_status_bar_snapshot()
        assert snap["jatevo_quota_label"] is None


class TestAppendStatusBarFragments:
    def test_cost_fragments_skipped_when_no_label(self):
        cli = _make_cli()
        frags: list = []
        cli._append_status_bar_cost_fragments(frags, {"usage": {}}, 40)
        assert frags == []

    def test_cost_fragments_added_when_label_present(self):
        cli = _attach_agent(_make_cli())
        snap = cli._get_status_bar_snapshot()
        frags: list = []
        cli._append_status_bar_cost_fragments(frags, snap, 120)
        classes = [c for c, _ in frags]
        assert "class:status-bar-cost" in classes

    def test_throughput_fragments_skipped_when_disabled(self):
        cli = _attach_agent(_make_cli())
        cli._show_status_bar_tps = False
        snap = cli._get_status_bar_snapshot()
        frags: list = []
        cli._append_status_bar_throughput_fragments(frags, snap, 120)
        assert not any(c == "class:status-bar-tps" for c, _ in frags)

    def test_venice_quota_fragments_when_present(self):
        cli = _make_cli()
        snap = {"venice_quota_label": "VN 10%", "venice_quota_percent": 10}
        frags: list = []
        cli._append_status_bar_provider_quota_fragments(frags, snap)
        texts = [t for _, t in frags]
        assert "VN 10%" in texts


class TestBuildStatusBarText:
    def test_narrow_width_omits_cost(self):
        cli = _attach_agent(_make_cli())
        text = cli._build_status_bar_text(width=48)
        assert "claude-sonnet" in text
        assert "$" not in text

    def test_wide_width_includes_cost(self):
        cli = _attach_agent(_make_cli())
        text = cli._build_status_bar_text(width=120)
        assert "$" in text

    def test_exception_fallback_uses_model_name(self):
        cli = _make_cli(model="fallback-model")
        with patch.object(cli, "_get_status_bar_snapshot", side_effect=RuntimeError("snap")):
            text = cli._build_status_bar_text(width=120)
        assert "fallback-model" in text

    def test_get_status_bar_fragments_empty_when_hidden(self):
        cli = _attach_agent(_make_cli())
        cli._status_bar_visible = False
        assert cli._get_status_bar_fragments() == []

    def test_get_status_bar_fragments_empty_during_model_picker(self):
        cli = _attach_agent(_make_cli())
        cli._model_picker_state = {"open": True}
        assert cli._get_status_bar_fragments() == []


class TestPackStatusBarFragmentRows:
    def test_single_line_when_no_metrics(self):
        cli = _make_cli()
        header = [("class:status-bar", "hdr")]
        metric: list = []
        rows = cli._pack_status_bar_fragment_rows(header, metric, 80)
        assert cli._status_bar_layout_lines == 1
        assert rows == header

    def test_zero_width_coerced_to_one(self):
        cli = _make_cli()
        header = [("class:status-bar", "x")]
        metric = [("class:status-bar-dim", "y")]
        cli._pack_status_bar_fragment_rows(header, metric, 0)
        assert cli._status_bar_layout_lines >= 1
