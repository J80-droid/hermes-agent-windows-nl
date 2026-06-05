#!/usr/bin/env python3
"""Verify fork status-bar prompt-timer via overlay (Tier A cli.py unchanged).

Checks overlay module presence, runtime patch on HermesCLI, and
``format_prompt_elapsed_status_bar(show_emoji=False)`` smoke.

Usage:
    python scripts/verify_fork_status_bar_display.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OVERLAY_MODULE = REPO / "overlay" / "hermes_cli" / "status_bar_prompt_elapsed.py"


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _check_overlay_module() -> None:
    if not OVERLAY_MODULE.is_file():
        _fail(f"missing {OVERLAY_MODULE.relative_to(REPO)}")
    _ok("overlay status_bar_prompt_elapsed.py present")


def _check_runtime_patch() -> None:
    sys.path.insert(0, str(REPO))
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    if not getattr(HermesCLI, "_fork_status_bar_patch_applied", False):
        _fail("HermesCLI missing _fork_status_bar_patch_applied after bootstrap")
    if not hasattr(HermesCLI, "_format_prompt_elapsed"):
        _fail("HermesCLI missing _format_prompt_elapsed after overlay patch")
    mixin = HermesCLI._format_prompt_elapsed
    if getattr(mixin, "__func__", mixin).__name__ != "_format_prompt_elapsed":
        _fail("unexpected _format_prompt_elapsed binding")
    _ok("HermesCLI prompt-elapsed via overlay cli_fork_patch")


def _check_smoke_no_emoji() -> None:
    sys.path.insert(0, str(REPO))
    from overlay.bootstrap import install

    install()
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
    _check_overlay_module()
    _check_runtime_patch()
    _check_smoke_no_emoji()
    print("verify_fork_status_bar_display: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
