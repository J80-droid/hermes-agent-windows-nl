#!/usr/bin/env python3
"""Verify fork-owned rich status-bar cost wiring (post-merge drift guard)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify rich status-bar cost wiring")
    parser.add_argument("--verify", action="store_true", help="Exit 1 on drift")
    args = parser.parse_args()

    repo = _repo()
    errors: list[str] = []

    defaults = (repo / "windows" / "team_display.defaults").read_text(encoding="utf-8")
    if "show_cost=true" not in defaults:
        errors.append("team_display.defaults missing show_cost=true")
    if "cost_bar_mode=rich" not in defaults:
        errors.append("team_display.defaults missing cost_bar_mode=rich")

    gateway = (repo / "tui_gateway" / "server.py").read_text(encoding="utf-8")
    if "build_session_usage_snapshot" not in gateway:
        errors.append("tui_gateway/server.py missing build_session_usage_snapshot delegatie")

    snapshot = repo / "hermes_cli" / "usage_snapshot.py"
    if not snapshot.is_file():
        errors.append("hermes_cli/usage_snapshot.py ontbreekt")

    cost_bar = repo / "ui-tui" / "src" / "domain" / "usageCostBar.ts"
    if not cost_bar.is_file():
        errors.append("ui-tui/src/domain/usageCostBar.ts ontbreekt")
    else:
        text = cost_bar.read_text(encoding="utf-8")
        if "formatStatusBarCostRich" not in text:
            errors.append("usageCostBar.ts mist formatStatusBarCostRich")

    chrome = (repo / "ui-tui" / "src" / "components" / "appChrome.tsx").read_text(encoding="utf-8")
    if "formatStatusBarCostRich" not in chrome:
        errors.append("appChrome.tsx gebruikt formatStatusBarCostRich niet")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return 1

    print("[OK] rich status-bar cost wiring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
