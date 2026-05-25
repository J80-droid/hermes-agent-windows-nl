#!/usr/bin/env python3
"""E2E: classic CLI ``_pending_input`` queue visibility and management.

Covers cli_pending_queue helpers + HermesCLI integration (no live API, no TUI).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0
STEP = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _make_cli(config_overrides=None):
    clean_config = {
        "model": {
            "default": "anthropic/claude-opus-4.6",
            "base_url": "https://openrouter.ai/api/v1",
            "provider": "auto",
        },
        "display": {"compact": False, "tool_progress": "all"},
        "agent": {},
        "terminal": {"env_type": "local"},
    }
    if config_overrides:
        clean_config.update(config_overrides)
    clean_env = {"LLM_MODEL": "", "HERMES_MAX_ITERATIONS": ""}
    prompt_toolkit_stubs = {
        "prompt_toolkit": MagicMock(),
        "prompt_toolkit.history": MagicMock(),
        "prompt_toolkit.styles": MagicMock(),
        "prompt_toolkit.patch_stdout": MagicMock(),
        "prompt_toolkit.application": MagicMock(),
        "prompt_toolkit.layout": MagicMock(),
        "prompt_toolkit.layout.processors": MagicMock(),
        "prompt_toolkit.filters": MagicMock(),
        "prompt_toolkit.layout.dimension": MagicMock(),
        "prompt_toolkit.layout.menus": MagicMock(),
        "prompt_toolkit.widgets": MagicMock(),
        "prompt_toolkit.key_binding": MagicMock(),
        "prompt_toolkit.completion": MagicMock(),
        "prompt_toolkit.formatted_text": MagicMock(),
        "prompt_toolkit.auto_suggest": MagicMock(),
    }
    import importlib

    with patch.dict(sys.modules, prompt_toolkit_stubs), patch.dict(
        "os.environ", clean_env, clear=False
    ):
        import cli as cli_mod

        cli_mod = importlib.reload(cli_mod)
        with patch.object(cli_mod, "get_tool_definitions", return_value=[]), patch.dict(
            cli_mod.__dict__, {"CLI_CONFIG": clean_config}
        ):
            return cli_mod.HermesCLI()


def test_e1_fifo_snapshot_order() -> None:
    from hermes_cli.cli_pending_queue import pending_queue_depth, snapshot_pending_queue

    q = queue.Queue()
    for item in ("first", "second", "third"):
        q.put(item)
    snap = snapshot_pending_queue(q)
    ok = snap == ["first", "second", "third"] and pending_queue_depth(q) == 3
    _step("FIFO snapshot behoudt enqueue-volgorde", ok)


def test_e2_list_mode_render_cap_and_overflow() -> None:
    from hermes_cli.cli_pending_queue import render_queue_lines

    entries = [f"item{i}" for i in range(10)]
    lines = render_queue_lines(entries, width=100, list_mode=True)
    ok = (
        lines[0] == "  queued (10)"
        and any("1. item0" in ln for ln in lines)
        and any("…and 2 more" in ln for ln in lines)
        and sum(1 for ln in lines if ln.strip().startswith(tuple(f"{i}." for i in range(1, 9)))) == 8
    )
    _step("/queue list: max 8 regels + overflow-hint", ok)


def test_e3_pop_fifo_head() -> None:
    from hermes_cli.cli_pending_queue import pop_pending_head, snapshot_pending_queue

    q = queue.Queue()
    q.put("a")
    q.put("b")
    head = pop_pending_head(q)
    ok = head == "a" and snapshot_pending_queue(q) == ["b"]
    _step("/queue pop verwijdert FIFO-head", ok)


def test_e4_clear_drains_queue() -> None:
    from hermes_cli.cli_pending_queue import clear_pending_queue, pending_queue_depth

    q = queue.Queue()
    q.put("x")
    q.put("y")
    removed = clear_pending_queue(q)
    ok = removed == 2 and pending_queue_depth(q) == 0
    _step("/queue clear leegt volledige wachtrij", ok)


def test_e5_pop_empty_no_crash() -> None:
    from hermes_cli.cli_pending_queue import pop_pending_head

    q = queue.Queue()
    ok = pop_pending_head(q) is None
    _step("pop op lege queue → None", ok)


def test_e6_slash_command_label() -> None:
    from hermes_cli.cli_pending_queue import normalize_pending_entry

    label = normalize_pending_entry("/subgoal finish tests")
    ok = label == "[cmd] /subgoal finish tests"
    _step("slash-command in queue → [cmd] prefix", ok)


def test_e7_tuple_images_label() -> None:
    from hermes_cli.cli_pending_queue import normalize_pending_entry

    label = normalize_pending_entry(("analyze", [Path("a.png"), Path("b.png")]))
    ok = label == "analyze [2 images]"
    _step("tuple+images → [N images] suffix", ok)


def test_e8_enqueue_ack_running_vs_idle() -> None:
    from hermes_cli.cli_pending_queue import enqueue_ack_message

    busy = enqueue_ack_message("follow", depth=2, agent_running=True)
    idle = enqueue_ack_message("follow", depth=1, agent_running=False)
    ok = "[2]" in busy and "next turn" in busy and "[1]" in idle and "when idle" in idle
    _step("enqueue ack: next turn vs when idle", ok)


def test_e9_status_fragment_depth_gate() -> None:
    from hermes_cli.cli_pending_queue import queue_status_fragment

    ok = queue_status_fragment(0) is None and queue_status_fragment(3) == "queue:3"
    _step("statusbalk fragment alleen bij depth > 0", ok)


def test_e10_hint_narrow_layout_and_height() -> None:
    from hermes_cli.cli_pending_queue import hint_panel_height, render_queue_lines

    lines = render_queue_lines(["one", "two"], width=50, max_visible=2)
    height = hint_panel_height(2, 50)
    ok = (
        lines[0] == "  queued (2)"
        and any("/queue list" in ln for ln in lines)
        and height == 2
    )
    _step("smalle terminal: compact hint + height=2", ok)


def test_e11_format_removed_preview() -> None:
    from hermes_cli.cli_pending_queue import format_removed_preview

    raw = "\x1b[31m" + ("z" * 120) + "\x1b[0m"
    out = format_removed_preview(raw, max_len=40)
    ok = len(out) == 40 and out.endswith("…") and "\x1b" not in out
    _step("pop-preview: ANSI-strip + ellipsis", ok)


def test_e12_hermes_cli_process_command_fifo() -> None:
    cli = _make_cli()
    cli.process_command("/queue first")
    cli.process_command("/queue second")
    cli.process_command("/queue third")
    ok = cli._pending_queue_entries() == ["first", "second", "third"]
    _step("HermesCLI: drie× /queue → snapshot FIFO", ok)


def test_e13_hermes_cli_pop_and_clear() -> None:
    cli = _make_cli()
    cli.process_command("/queue one")
    cli.process_command("/queue two")
    cli.process_command("/queue pop")
    remaining = cli._pending_input.get_nowait()
    cli.process_command("/queue clear")
    ok = remaining == "two" and cli._pending_input.empty()
    _step("HermesCLI: pop head + clear", ok)


def test_e14_hermes_cli_q_alias() -> None:
    cli = _make_cli()
    ok = cli.process_command("/q alias payload") is True
    if ok:
        ok = cli._pending_input.get_nowait() == "alias payload"
    _step("HermesCLI: /q alias → queue (niet quit)", ok)


def test_e15_hermes_cli_hint_blocked_command_running() -> None:
    cli = _make_cli()
    cli._command_running = True
    ok = cli._queue_hint_blocked()
    _step("HermesCLI: hint geblokkeerd bij _command_running", ok)


def test_e16_hermes_cli_status_bar_queue_fragment() -> None:
    cli = _make_cli()
    cli.process_command("/queue status probe")
    parts: list = []
    cli._append_pending_queue_status_part(parts)
    ok = parts == ["queue:1"]
    _step("HermesCLI: statusbalk bevat queue:N", ok)


def test_e17_pytest_queue_regression_gate() -> None:
    tests = [
        REPO_ROOT / "tests" / "hermes_cli" / "test_cli_pending_queue.py",
        REPO_ROOT / "tests" / "cli" / "test_cli_init.py",
    ]
    for path in tests:
        if not path.is_file():
            _step("pytest queue-regressie", False, f"ontbreekt: {path.name}")
            return
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *(str(t) for t in tests),
                "-q",
                "-k",
                "queue or pending",
                "--tb=short",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=False,
            env=env,
        )
    except Exception as exc:
        _step("pytest queue-regressie (unit + cli_init)", False, str(exc))
        return
    tail = (proc.stdout or proc.stderr or "")[-400:]
    ok = proc.returncode == 0
    _step("pytest queue-regressie (unit + cli_init)", ok, tail.strip() if not ok else "")


def main() -> int:
    print("=== CliPendingQueue E2E ===")
    test_e1_fifo_snapshot_order()
    test_e2_list_mode_render_cap_and_overflow()
    test_e3_pop_fifo_head()
    test_e4_clear_drains_queue()
    test_e5_pop_empty_no_crash()
    test_e6_slash_command_label()
    test_e7_tuple_images_label()
    test_e8_enqueue_ack_running_vs_idle()
    test_e9_status_fragment_depth_gate()
    test_e10_hint_narrow_layout_and_height()
    test_e11_format_removed_preview()
    test_e12_hermes_cli_process_command_fifo()
    test_e13_hermes_cli_pop_and_clear()
    test_e14_hermes_cli_q_alias()
    test_e15_hermes_cli_hint_blocked_command_running()
    test_e16_hermes_cli_status_bar_queue_fragment()
    test_e17_pytest_queue_regression_gate()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
