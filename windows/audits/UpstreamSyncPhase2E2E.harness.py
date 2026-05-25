#!/usr/bin/env python3
"""E2E harness: upstream_sync fase-2 merge + pip-na-merge + TUI status-rule alignment."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def check_upstream_sync_phase2(failures: list[str]) -> None:
    ps1 = _read("windows/upstream_sync.ps1").replace("\r\n", "\n")

    required = [
        "function Invoke-UpstreamGitMergeIfBehind",
        "$script:LastUpstreamMergedCount = 0",
        "$script:UpstreamPreflightFetched = $true",
        "if (-not $script:UpstreamPreflightFetched)",
        "$upstreamRef = 'upstream/main'",
        "git rev-parse --verify $upstreamRef",
        "'HEAD..' + $upstreamRef",
        "git rev-list --count $behindRange",
        "Test-NativeCommandFailed",
        "function Install-HermesEditablePythonAfterUpstreamMerge",
        "pip install editable na upstream-merge",
        "$pipEditableFlag = '-e'",
        "$pipInstallArgs",
        "$script:LastUpstreamMergedCount -gt 0",
        "Install-HermesEditablePythonAfterUpstreamMerge -CondaExe $conda",
    ]
    for needle in required:
        if needle not in ps1:
            _fail(f"upstream_sync.ps1 mist: {needle!r}", failures)

    hermes_block = re.search(
        r"(?s)function Invoke-HermesUpdate\s*\{.*?(?=function |\Z)",
        ps1,
    )
    if not hermes_block:
        _fail("upstream_sync: Invoke-HermesUpdate blok ontbreekt", failures)
        return
    block = hermes_block.group(0)
    merge_call = block.find("$mergeCode = Invoke-UpstreamGitMergeIfBehind")
    pip_call = block.find("Install-HermesEditablePythonAfterUpstreamMerge -CondaExe")
    hermes_call = block.find("'hermes', 'update', '-y'")
    if merge_call < 0 or hermes_call < 0 or merge_call > hermes_call:
        _fail("upstream_sync: merge moet vóór hermes update in Invoke-HermesUpdate", failures)
    if pip_call >= 0 and (pip_call < merge_call or pip_call > hermes_call):
        _fail("upstream_sync: pip-na-merge moet tussen merge-call en hermes update", failures)

    preflight_fetch = ps1.find("$script:UpstreamPreflightFetched = $true")
    merge_fetch_guard = ps1.find("if (-not $script:UpstreamPreflightFetched)")
    if preflight_fetch < 0 or merge_fetch_guard < 0 or preflight_fetch > merge_fetch_guard:
        _fail("upstream_sync: preflight moet UpstreamPreflightFetched zetten vóór merge-guard", failures)


def check_tui_status_rule_alignment(failures: list[str]) -> None:
    ucb = _read("ui-tui/src/domain/usageCostBar.ts")
    app = _read("ui-tui/src/components/appChrome.tsx")

    if "export function statusRuleMinLeftWidth" not in ucb:
        _fail("usageCostBar: statusRuleMinLeftWidth ontbreekt", failures)
    if "leftWidth?:" not in ucb and "leftWidth?: number" not in ucb:
        if "leftWidth?:" not in ucb:
            _fail("usageCostBar: leftWidth opt in resolveStatusRuleLayout ontbreekt", failures)
    if "statusRuleMinLeftWidth" not in app:
        _fail("appChrome: statusRuleMinLeftWidth import/gebruik ontbreekt", failures)
    if "leftWidth," not in app and "leftWidth\n" not in app:
        if re.search(r"leftWidth\s*,", app) is None:
            _fail("appChrome: leftWidth niet doorgegeven aan resolveStatusRuleLayout", failures)

    block = re.search(
        r"resolveStatusRuleLayout\(\{[^}]+\}\)",
        app,
        re.DOTALL,
    )
    if not block or "leftWidth" not in block.group(0):
        _fail("appChrome: resolveStatusRuleLayout-call mist leftWidth", failures)


def main() -> int:
    failures: list[str] = []
    check_upstream_sync_phase2(failures)
    check_tui_status_rule_alignment(failures)
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("OK: upstream_sync phase2 + TUI status-rule harness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
