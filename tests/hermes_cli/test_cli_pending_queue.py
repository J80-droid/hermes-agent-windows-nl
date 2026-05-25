"""Unit tests for hermes_cli.cli_pending_queue."""

from __future__ import annotations

import queue
from pathlib import Path

import pytest

from hermes_cli.cli_pending_queue import (
    clear_pending_queue,
    enqueue_ack_message,
    format_queue_preview,
    hint_panel_height,
    normalize_pending_entry,
    pending_queue_depth,
    pop_pending_head,
    queue_status_fragment,
    render_queue_lines,
    snapshot_pending_queue,
)


class TestNormalizePendingEntry:
    def test_plain_text(self):
        assert normalize_pending_entry("hello") == "hello"

    def test_tuple_with_images(self):
        assert normalize_pending_entry(("analyze this", [Path("a.png"), Path("b.png")])) == (
            "analyze this [2 images]"
        )

    def test_slash_command_prefix(self):
        assert normalize_pending_entry("/subgoal finish tests").startswith("[cmd] ")

    def test_empty_string(self):
        assert normalize_pending_entry("") == "(empty)"


class TestSnapshotAndDepth:
    def test_fifo_order_preserved(self):
        q = queue.Queue()
        q.put("first")
        q.put("second")
        assert snapshot_pending_queue(q) == ["first", "second"]
        assert pending_queue_depth(q) == 2

    def test_pop_head(self):
        q = queue.Queue()
        q.put("a")
        q.put("b")
        assert pop_pending_head(q) == "a"
        assert snapshot_pending_queue(q) == ["b"]

    def test_clear(self):
        q = queue.Queue()
        q.put("a")
        q.put("b")
        assert clear_pending_queue(q) == 2
        assert pending_queue_depth(q) == 0


class TestRenderQueueLines:
    def test_list_mode_caps_at_eight(self):
        entries = [f"item{i}" for i in range(10)]
        lines = render_queue_lines(entries, width=100, list_mode=True)
        numbered = [ln for ln in lines if ln.strip().startswith(tuple(str(i) for i in range(1, 10)))]
        assert any("…and 2 more" in ln for ln in lines)

    def test_hint_narrow_terminal(self):
        lines = render_queue_lines(["one", "two"], width=50, max_visible=2)
        assert lines[0] == "  queued (2)"
        assert any("/queue list" in ln for ln in lines)

    def test_preview_ellipsis(self):
        long = "x" * 100
        out = format_queue_preview(long, 20)
        assert out.endswith("…")
        assert len(out) == 20


class TestHelpers:
    def test_queue_status_fragment(self):
        assert queue_status_fragment(0) is None
        assert queue_status_fragment(3) == "queue:3"

    def test_enqueue_ack(self):
        msg = enqueue_ack_message("follow up", depth=2, agent_running=True)
        assert "[2]" in msg
        assert "next turn" in msg

    def test_hint_panel_height(self):
        assert hint_panel_height(0, 120) == 0
        assert hint_panel_height(3, 120) >= 2
        assert hint_panel_height(2, 40) == 1
