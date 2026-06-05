#!/usr/bin/env python3
"""Verify fork-owned rich status-bar cost wiring (post-merge drift guard)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


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

    gateway_path = repo / "tui_gateway" / "server.py"
    if gateway_path.is_file():
        gateway = gateway_path.read_text(encoding="utf-8")
        if "usage" not in gateway.lower() and "snapshot" not in gateway.lower():
            errors.append("tui_gateway/server.py mist usage/snapshot delegatie (upstream of overlay)")

    snapshot = repo / "overlay" / "hermes_cli" / "usage_snapshot.py"
    if not snapshot.is_file():
        errors.append("overlay/hermes_cli/usage_snapshot.py ontbreekt")

    status_bar_cost = repo / "overlay" / "hermes_cli" / "status_bar_cost.py"
    if not status_bar_cost.is_file():
        errors.append("overlay/hermes_cli/status_bar_cost.py ontbreekt")
    else:
        sbc = status_bar_cost.read_text(encoding="utf-8")
        for needle in (
            "format_session_cost_label",
            "format_status_bar_cost_rich",
            "resolve_status_bar_cost_label",
        ):
            if needle not in sbc:
                errors.append(f"status_bar_cost.py mist {needle}")

    patch_py = repo / "overlay" / "hermes_cli" / "cli_fork_patch.py"
    if not patch_py.is_file():
        errors.append("overlay/hermes_cli/cli_fork_patch.py ontbreekt")
    else:
        patch_text = patch_py.read_text(encoding="utf-8")
        for needle in (
            "_append_status_bar_cost_fragments",
            "_resolve_status_bar_cost_label",
            "apply_cli_fork_patch",
        ):
            if needle not in patch_text:
                errors.append(f"cli_fork_patch.py mist overlay hook: {needle}")

    bootstrap_py = (repo / "overlay" / "bootstrap.py").read_text(encoding="utf-8")
    if "apply_cli_fork_patch" not in bootstrap_py:
        errors.append("overlay/bootstrap.py roept apply_cli_fork_patch niet aan")

    cost_tests = repo / "tests" / "hermes_cli" / "test_status_bar_cost.py"
    if not cost_tests.is_file():
        errors.append("tests/hermes_cli/test_status_bar_cost.py ontbreekt")

    classic_smoke = repo / "scripts" / "status_bar_cost_classic_cli_smoke.py"
    if not classic_smoke.is_file():
        errors.append("scripts/status_bar_cost_classic_cli_smoke.py ontbreekt")

    classic_live = repo / "scripts" / "status_bar_cost_classic_cli_live_smoke.py"
    if not classic_live.is_file():
        errors.append("scripts/status_bar_cost_classic_cli_live_smoke.py ontbreekt")

    classic_e2e = repo / "windows" / "audits" / "RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1"
    if not classic_e2e.is_file():
        errors.append("windows/audits/RUN_CLASSIC_CLI_STATUS_BAR_COST_E2E.ps1 ontbreekt")

    usage_pricing = repo / "agent" / "usage_pricing.py"
    if usage_pricing.is_file():
        up_text = usage_pricing.read_text(encoding="utf-8")
        if "cost" not in up_text.lower() and "pricing" not in up_text.lower():
            errors.append("agent/usage_pricing.py mist pricing/cost catalog (Tier A upstream)")

    cost_bar = repo / "overlay" / "ui-tui" / "src" / "domain" / "usageCostBar.ts"
    if not cost_bar.is_file():
        errors.append("overlay/ui-tui/src/domain/usageCostBar.ts ontbreekt")
    else:
        text = cost_bar.read_text(encoding="utf-8")
        for needle in (
            "formatStatusBarCostRich",
            "resolveStatusRuleLayout",
            "statusRuleColumns",
            "formatSessionCostLabel",
            "shouldShowStatusBarCostRich",
        ):
            if needle not in text:
                errors.append(f"usageCostBar.ts mist {needle}")

    chrome_path = repo / "ui-tui" / "src" / "components" / "appChrome.tsx"
    overlay_cost = repo / "overlay" / "ui-tui" / "src" / "domain" / "usageCostBar.ts"
    if chrome_path.is_file():
        chrome = chrome_path.read_text(encoding="utf-8")
        if "resolveStatusRuleLayout" not in chrome:
            if not overlay_cost.is_file() or "resolveStatusRuleLayout" not in overlay_cost.read_text(
                encoding="utf-8"
            ):
                errors.append("TUI cost layout ontbreekt in appChrome en overlay/ui-tui")
    elif not overlay_cost.is_file():
        errors.append("overlay/ui-tui/src/domain/usageCostBar.ts ontbreekt")

    rebuild = repo / "windows" / "scripts" / "rebuild_tui.ps1"
    if not rebuild.is_file():
        errors.append("windows/scripts/rebuild_tui.ps1 ontbreekt")

    dist = repo / "ui-tui" / "dist" / "entry.js"
    if dist.is_file():
        dist_text = dist.read_text(encoding="utf-8", errors="ignore")
        if "resolveStatusRuleLayout" not in dist_text:
            errors.append(
                "ui-tui/dist/entry.js is stale (mist resolveStatusRuleLayout) — draai windows/REBUILD_TUI.bat"
            )
    else:
        errors.append("ui-tui/dist/entry.js ontbreekt — draai windows/REBUILD_TUI.bat")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return 1

    print("[OK] rich status-bar cost wiring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
