"""Unit tests for hermes_cli.cli_pending_queue.

Focus: FIFO helpers, display normalization, hint/status fragments.
Edge cases: invalid input, broken Queue peek, ANSI/control chars, slash detection.
"""

from __future__ import annotations

import queue
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, PropertyMock

import pytest

from hermes_cli.cli_pending_queue import (
    clear_pending_queue,
    enqueue_ack_message,
    format_queue_preview,
    format_removed_preview,
    hint_panel_fragments,
    hint_panel_height,
    normalize_pending_entry,
    pending_queue_depth,
    pop_pending_head,
    queue_status_fragment,
    render_queue_lines,
    snapshot_pending_queue,
)
from hermes_cli import cli_pending_queue as mod


class TestLooksLikeSlashCommand:
    """Private helper — slash vs path-like strings."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("/queue follow up", True),
            ("/subgoal finish", True),
            ("hello", False),
            ("", False),
            ("/", True),
            ("/path/to/file", False),
            ("https://example.com/foo", False),
            ("not/a/slash/command at start", False),
        ],
    )
    def test_slash_detection(self, text: str, expected: bool) -> None:
        assert mod._looks_like_slash_command(text) is expected

    def test_leading_whitespace_not_treated_as_slash_command(self) -> None:
        """normalize_pending_entry strips later; detector requires leading /."""
        assert mod._looks_like_slash_command("  /goal status") is False


class TestNormalizePendingEntryHappyPath:
    def test_plain_text(self) -> None:
        assert normalize_pending_entry("hello") == "hello"

    def test_whitespace_trimmed(self) -> None:
        assert normalize_pending_entry("  padded  ") == "padded"

    def test_tuple_with_images(self) -> None:
        assert normalize_pending_entry(("analyze this", [Path("a.png"), Path("b.png")])) == (
            "analyze this [2 images]"
        )

    def test_slash_command_prefix(self) -> None:
        assert normalize_pending_entry("/subgoal finish tests") == "[cmd] /subgoal finish tests"

    def test_single_image_singular_suffix(self) -> None:
        assert normalize_pending_entry(("pic", [Path("x.png")])) == "pic [1 image]"


class TestNormalizePendingEntryEdgeCases:
    @pytest.mark.parametrize(
        "entry,expected",
        [
            ("", "(empty)"),
            (None, "(empty)"),
            ((), "(empty)"),
            (("   ", None), "(empty)"),
        ],
    )
    def test_empty_payloads(self, entry, expected: str) -> None:
        assert normalize_pending_entry(entry) == expected

    def test_tuple_text_only_no_images_key(self) -> None:
        assert normalize_pending_entry(("solo",)) == "solo"

    def test_tuple_images_only_no_text(self) -> None:
        assert normalize_pending_entry(("", [Path("a.png")])) == "[1 image]"

    def test_images_as_str_not_counted_as_sequence(self) -> None:
        """str in images slot must not use len(images) — avoids counting characters."""
        assert normalize_pending_entry(("x", "not-a-list")) == "x"

    def test_images_as_bytes_not_counted(self) -> None:
        assert normalize_pending_entry(("x", b"\x00\x01")) == "x"

    def test_images_without_len_falls_back_to_one(self) -> None:
        class NoLen:
            pass

        assert normalize_pending_entry(("x", NoLen())) == "x [1 image]"

    def test_non_string_entry_coerced(self) -> None:
        assert normalize_pending_entry(42) == "42"
        assert normalize_pending_entry(["list", "item"]) == "['list', 'item']"

    def test_multiline_text_collapsed_to_single_line_label(self) -> None:
        assert normalize_pending_entry("line1\nline2") == "line1\nline2"

    def test_path_like_slash_not_cmd_prefix(self) -> None:
        assert normalize_pending_entry("/var/log/hermes.log") == "/var/log/hermes.log"


class TestSnapshotAndDepth:
    def test_none_queue_returns_empty_snapshot_and_zero_depth(self) -> None:
        assert snapshot_pending_queue(None) == []
        assert pending_queue_depth(None) == 0

    def test_fifo_order_preserved(self) -> None:
        q: Queue = queue.Queue()
        q.put("first")
        q.put("second")
        assert snapshot_pending_queue(q) == ["first", "second"]
        assert pending_queue_depth(q) == 2

    def test_snapshot_does_not_consume(self) -> None:
        q: Queue = queue.Queue()
        q.put("only")
        snapshot_pending_queue(q)
        assert q.get_nowait() == "only"

    def test_snapshot_normalizes_mixed_payloads(self) -> None:
        q: Queue = queue.Queue()
        q.put("/goal pause")
        q.put(("shots", [Path("a.png")]))
        assert snapshot_pending_queue(q) == [
            "[cmd] /goal pause",
            "shots [1 image]",
        ]

    def test_pop_head_fifo(self) -> None:
        q: Queue = queue.Queue()
        q.put("a")
        q.put("b")
        assert pop_pending_head(q) == "a"
        assert snapshot_pending_queue(q) == ["b"]

    def test_clear_returns_count_and_empties(self) -> None:
        q: Queue = queue.Queue()
        q.put("a")
        q.put("b")
        assert clear_pending_queue(q) == 2
        assert pending_queue_depth(q) == 0

    def test_pop_none_queue(self) -> None:
        assert pop_pending_head(None) is None

    def test_clear_none_queue(self) -> None:
        assert clear_pending_queue(None) == 0

    def test_pop_empty_queue(self) -> None:
        q: Queue = queue.Queue()
        assert pop_pending_head(q) is None

    def test_clear_already_empty(self) -> None:
        q: Queue = queue.Queue()
        assert clear_pending_queue(q) == 0

    def test_double_pop_second_returns_none(self) -> None:
        q: Queue = queue.Queue()
        q.put("one")
        assert pop_pending_head(q) == "one"
        assert pop_pending_head(q) is None

    def test_snapshot_when_queue_attr_raises(self) -> None:
        broken = MagicMock(spec=Queue)
        type(broken).queue = PropertyMock(side_effect=RuntimeError("peek denied"))
        assert snapshot_pending_queue(broken) == []

    def test_depth_when_qsize_and_len_fail(self) -> None:
        broken = MagicMock(spec=Queue)
        broken.qsize.side_effect = RuntimeError("no qsize")
        type(broken).queue = PropertyMock(side_effect=RuntimeError("no queue"))
        assert pending_queue_depth(broken) == 0

    def test_depth_fallback_to_len_when_qsize_fails(self) -> None:
        q = MagicMock(spec=Queue)
        q.qsize.side_effect = NotImplementedError("unreliable qsize")
        q.queue = ["a", "b"]
        assert pending_queue_depth(q) == 2


class TestFormatQueuePreview:
    def test_happy_path_short_text(self) -> None:
        assert format_queue_preview("hello", 20) == "hello"

    def test_ellipsis_when_over_width(self) -> None:
        long = "x" * 100
        out = format_queue_preview(long, 20)
        assert out.endswith("…")
        assert len(out) == 20

    def test_width_clamped_to_minimum_eight(self) -> None:
        assert len(format_queue_preview("abcdefghij", 3)) == 8

    def test_empty_after_strip_returns_empty_string(self) -> None:
        assert format_queue_preview("   ", 20) == ""
        assert format_queue_preview("\x00\x01", 20) == ""

    def test_ansi_stripped_before_measure(self) -> None:
        raw = "\x1b[31m" + ("z" * 50) + "\x1b[0m"
        out = format_queue_preview(raw, 10)
        assert "\x1b" not in out
        assert len(out) == 10

    def test_newlines_replaced_in_ansi_strip_path(self) -> None:
        out = format_queue_preview("a\nb\nc", 20)
        assert "\n" not in out
        assert "a b c" in out

    @pytest.mark.parametrize("width", [0, -5, 1])
    def test_extreme_width_values(self, width: int) -> None:
        out = format_queue_preview("hello world", width)
        assert len(out) >= 8


class TestRenderQueueLines:
    def test_empty_entries_queue_empty_message(self) -> None:
        lines = render_queue_lines([], width=80)
        assert lines == ["  (queue empty)"]

    def test_single_entry_numbered(self) -> None:
        lines = render_queue_lines(["only"], width=80, max_visible=2)
        assert lines[0] == "  queued (1)"
        assert any("1. only" in ln for ln in lines)

    def test_list_mode_caps_at_eight_with_overflow(self) -> None:
        entries = [f"item{i}" for i in range(10)]
        lines = render_queue_lines(entries, width=100, list_mode=True)
        assert lines[0] == "  queued (10)"
        assert any("…and 2 more" in ln for ln in lines)
        numbered = [ln for ln in lines if ". item" in ln]
        assert len(numbered) == 8

    def test_list_mode_overflow_suffix_pop_hint(self) -> None:
        entries = [f"item{i}" for i in range(9)]
        lines = render_queue_lines(entries, width=100, list_mode=True)
        assert any("(use /queue pop)" in ln for ln in lines)

    def test_hint_narrow_terminal_compact(self) -> None:
        lines = render_queue_lines(["one", "two"], width=50, max_visible=2)
        assert lines[0] == "  queued (2)"
        assert lines == ["  queued (2)", "  /queue list"]

    def test_hint_wide_shows_previews(self) -> None:
        lines = render_queue_lines(["alpha", "beta"], width=80, max_visible=2)
        assert any("1. alpha" in ln for ln in lines)
        assert any("2. beta" in ln for ln in lines)

    def test_hint_more_than_two_shows_and_more(self) -> None:
        lines = render_queue_lines(["a", "b", "c"], width=80, max_visible=2)
        assert any("…and 1 more" in ln for ln in lines)
        assert any("/queue list" in ln for ln in lines)

    def test_max_visible_zero_clamped_to_one_row(self) -> None:
        lines = render_queue_lines(["x", "y"], width=80, max_visible=0)
        assert any("1. x" in ln for ln in lines)
        assert any("…and 1 more" in ln for ln in lines)

    def test_width_boundary_60_uses_full_layout(self) -> None:
        lines_narrow = render_queue_lines(["a"], width=59)
        lines_wide = render_queue_lines(["a"], width=60)
        assert "/queue list" in "\n".join(lines_narrow)
        assert any("1. a" in ln for ln in lines_wide)

    def test_long_entry_preview_truncated_in_line(self) -> None:
        long = "z" * 200
        lines = render_queue_lines([long], width=80, list_mode=True)
        numbered = [ln for ln in lines if ln.strip().startswith("1.")]
        assert numbered
        assert "…" in numbered[0]


class TestQueueStatusFragment:
    @pytest.mark.parametrize("depth,expected", [
        (0, None),
        (-1, None),
        (-100, None),
        (1, "queue:1"),
        (99, "queue:99"),
    ])
    def test_depth_gate(self, depth: int, expected: str | None) -> None:
        assert queue_status_fragment(depth) == expected


class TestEnqueueAckMessage:
    def test_agent_running_next_turn(self) -> None:
        msg = enqueue_ack_message("follow up", depth=2, agent_running=True)
        assert msg == "[2] Queued for next turn: follow up"

    def test_agent_idle_when_idle(self) -> None:
        msg = enqueue_ack_message("follow up", depth=1, agent_running=False)
        assert "when idle" in msg
        assert "[1]" in msg

    def test_depth_zero_still_formats(self) -> None:
        msg = enqueue_ack_message("x", depth=0, agent_running=False)
        assert msg.startswith("[0]")

    def test_tuple_payload_normalized_in_ack(self) -> None:
        msg = enqueue_ack_message(
            ("see", [Path("a.png")]),
            depth=3,
            agent_running=True,
        )
        assert "[3]" in msg
        assert "[1 image]" in msg

    def test_slash_payload_cmd_prefix_in_ack(self) -> None:
        msg = enqueue_ack_message("/queue list", depth=1, agent_running=True)
        assert "[cmd]" in msg

    def test_long_payload_preview_truncated(self) -> None:
        msg = enqueue_ack_message("w" * 200, depth=1, agent_running=True)
        assert len(msg) < 250
        assert "…" in msg


class TestHintPanelHeight:
    def test_zero_depth_zero_height(self) -> None:
        assert hint_panel_height(0, 120) == 0

    def test_negative_depth_treated_as_no_panel(self) -> None:
        assert hint_panel_height(-3, 120) == 0

    def test_narrow_terminal_two_lines(self) -> None:
        assert hint_panel_height(2, 40) == 2
        assert hint_panel_height(5, 59) == 2

    def test_wide_depth_one(self) -> None:
        assert hint_panel_height(1, 80) == 2

    def test_wide_depth_two_no_extra_footer(self) -> None:
        assert hint_panel_height(2, 80) == 3

    def test_wide_depth_three_includes_and_more_row(self) -> None:
        assert hint_panel_height(3, 80) == 4

    def test_width_boundary_60_uses_wide_formula(self) -> None:
        assert hint_panel_height(3, 60) == 4


class TestHintPanelFragments:
    def test_returns_hint_class_tuples(self) -> None:
        frags = hint_panel_fragments(["a", "b"], terminal_width=80)
        assert frags
        assert all(style == "class:hint" for style, _ in frags)
        assert all(isinstance(text, str) for _, text in frags)

    def test_empty_entries_still_one_fragment(self) -> None:
        frags = hint_panel_fragments([], terminal_width=80)
        assert len(frags) == 1
        assert "(queue empty)" in frags[0][1]

    def test_narrow_matches_render_line_count(self) -> None:
        frags = hint_panel_fragments(["x", "y"], terminal_width=50)
        assert len(frags) == 2


class TestFormatRemovedPreview:
    def test_short_unchanged(self) -> None:
        assert format_removed_preview("ok", max_len=80) == "ok"

    def test_long_uses_ellipsis(self) -> None:
        out = format_removed_preview("y" * 120, max_len=40)
        assert len(out) == 40
        assert out.endswith("…")

    def test_ansi_stripped(self) -> None:
        raw = "\x1b[1m" + ("a" * 50) + "\x1b[0m"
        out = format_removed_preview(raw, max_len=20)
        assert "\x1b" not in out

    def test_control_chars_removed(self) -> None:
        out = format_removed_preview("ok\x07tail", max_len=80)
        assert "\x07" not in out

    def test_max_len_zero_clamps_via_preview_width(self) -> None:
        """max_len=0 still flows through format_queue_preview(min width 8)."""
        out = format_removed_preview("hello", max_len=0)
        assert out == "hello"
        long_out = format_removed_preview("x" * 50, max_len=0)
        assert len(long_out) == 8
        assert long_out.endswith("…")


class TestStripAnsiPrivate:
    def test_strips_codes_and_flattens_newlines(self) -> None:
        assert mod._strip_ansi("a\x1b[31mb\x1b[0m\nc") == "ab c"


class TestIntegrationPopClearSnapshot:
    """Multi-step flows without mocking."""

    def test_pop_until_empty_then_clear_noop(self) -> None:
        q: Queue = queue.Queue()
        for i in range(3):
            q.put(f"n{i}")
        assert pop_pending_head(q) == "n0"
        assert pop_pending_head(q) == "n1"
        assert pop_pending_head(q) == "n2"
        assert pop_pending_head(q) is None
        assert clear_pending_queue(q) == 0

    def test_clear_then_snapshot_empty_message(self) -> None:
        q: Queue = queue.Queue()
        q.put("gone")
        clear_pending_queue(q)
        assert snapshot_pending_queue(q) == []
        lines = render_queue_lines(snapshot_pending_queue(q), width=80, list_mode=True)
        assert lines == ["  (queue empty)"]
