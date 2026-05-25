#!/usr/bin/env python3
"""Verify fork status-bar prompt-timer hooks survive upstream merges.

Checks that ``cli.py`` delegates ``_format_prompt_elapsed`` to
``hermes_cli.status_bar_prompt_elapsed`` (no inline ⏱/⏲) and that
``display.show_prompt_timer_emoji`` defaults to false.

Run after ``MERGE_UPSTREAM.bat -FinalizeOnly`` or when touching ``cli.py`` status bar.

Usage:
    python scripts/verify_fork_status_bar_display.py
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "cli.py"
MODULE = REPO / "hermes_cli" / "status_bar_prompt_elapsed.py"
CONFIG = REPO / "hermes_cli" / "config.py"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _check_module_exists() -> None:
    if not MODULE.is_file():
        _fail(f"missing {MODULE.relative_to(REPO)}")
    _ok("status_bar_prompt_elapsed.py present")


def _check_config_default() -> None:
    text = CONFIG.read_text(encoding="utf-8")
    if '"show_prompt_timer_emoji": False' not in text and "'show_prompt_timer_emoji': False" not in text:
        _fail("DISPLAY_DEFAULTS must set show_prompt_timer_emoji to False")
    _ok("show_prompt_timer_emoji default False in config")


def _extract_format_prompt_elapsed_source(cli_text: str) -> str:
    try:
        tree = ast.parse(cli_text)
    except SyntaxError as exc:
        _fail(f"cli.py parse error: {exc}")
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "HermesCLI":
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "_format_prompt_elapsed":
                seg = ast.get_source_segment(cli_text, item) or ""
                return seg
    _fail("_format_prompt_elapsed not found on HermesCLI")
    return ""


def _check_cli_delegates() -> None:
    if not CLI.is_file():
        _fail("missing cli.py")
    cli_text = CLI.read_text(encoding="utf-8")
    seg = _extract_format_prompt_elapsed_source(cli_text)
    if "status_bar_prompt_elapsed" not in seg:
        _fail("_format_prompt_elapsed must import/delegate to status_bar_prompt_elapsed")
    if "format_prompt_elapsed_status_bar" not in seg:
        _fail("_format_prompt_elapsed must call format_prompt_elapsed_status_bar")
    if "show_emoji" not in seg and "_show_prompt_timer_emoji" not in seg:
        _fail("_format_prompt_elapsed must pass show_emoji from _show_prompt_timer_emoji")
    if re.search(r'return\s+f"\{emoji\}', seg):
        _fail("_format_prompt_elapsed still returns inline emoji (upstream body not delegated)")
    if ("\u23f1" in seg or "\u23f2" in seg) and "format_prompt_elapsed_status_bar" not in seg:
        _fail("_format_prompt_elapsed still contains hardcoded timer emoji literals")
    _ok("cli.py delegates _format_prompt_elapsed to fork module")


def _check_smoke_no_emoji() -> None:
    sys.path.insert(0, str(REPO))
    from hermes_cli.status_bar_prompt_elapsed import (
        format_prompt_elapsed_status_bar,
        prompt_elapsed_contains_emoji,
    )

    out = format_prompt_elapsed_status_bar(None, 26.0, show_emoji=False)
    if prompt_elapsed_contains_emoji(out):
        _fail(f"show_emoji=False produced emoji: {out!r}")
    if "26s" not in out:
        _fail(f"expected 26s in output, got {out!r}")
    _ok("format_prompt_elapsed_status_bar(show_emoji=False) smoke")


def main() -> int:
    _check_module_exists()
    _check_config_default()
    _check_cli_delegates()
    _check_smoke_no_emoji()
    print("verify_fork_status_bar_display: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
