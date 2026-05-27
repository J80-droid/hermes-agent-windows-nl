#!/usr/bin/env python3
"""E2E: codebase-viz + dashboard launch integratie (structuur, geen live pygount).

Draai: audits/RUN_CODEBASE_VIZ_LAUNCH_E2E.bat
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PS1 = REPO / "windows/scripts/launch_dashboard_on_start.ps1"
LAUNCH_BAT = REPO / "start_hermes.bat"
VERIFY = REPO / "audits/verify_codebase_viz_health.py"
DIST_JS = REPO / "plugins/codebase-viz/dashboard/dist/index.js"
MANIFEST = REPO / "plugins/codebase-viz/dashboard/manifest.json"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] C{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] C{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def test_c1_launch_ps1_workspace_plugins() -> None:
    ps1 = PS1.read_text(encoding="utf-8")
    checks = [
        "Initialize-WorkspaceDashboardPlugins" in ps1,
        "HERMES_BUNDLED_PLUGINS" in ps1,
        "Install-HermesWebDashboardPackage" in ps1,
        "[web]" in ps1,
        "HERMES_DASHBOARD_OPEN_PATH" in ps1,
        "Open-DashboardBrowserIfRequested" in ps1,
        "Stop-HermesDashboardProcess" in ps1,
        "CODEBASE_VIZ_PYGOUNT_TIMEOUT" in ps1,
        "New-CondaDashboardRunArgs" in ps1,
    ]
    _step("launch_dashboard_on_start.ps1 contract", all(checks), f"{sum(checks)}/{len(checks)}")


def test_c2_start_hermes_no_default_browser_tab() -> None:
    win = (REPO / "windows/launch_hermes.bat").read_text(encoding="utf-8")
    ok = (
        "launch_dashboard_on_start.ps1" in win
        and 'set "HERMES_DASHBOARD_OPEN_PATH=/codebase-viz"' not in win
    )
    _step("start_hermes.bat geen default browser-tab", ok)


def test_c3_frontend_single_progress_bar() -> None:
    if not DIST_JS.is_file():
        _step("dist single progress bar", False, "dist/index.js ontbreekt - npm run build")
        return
    js = DIST_JS.read_text(encoding="utf-8", errors="replace")
    ok = (
        "codebase-viz-progress-track" in js
        and "codebase-viz-progress-native" not in js
        and "codebase-viz-scan-target" in js
    )
    _step("dist single progress bar", ok)


def test_c4_verify_health_module() -> None:
    os.environ["CODEBASE_VIZ_PYGOUNT_TIMEOUT"] = "240"
    sys.path.insert(0, str(REPO / "audits"))
    try:
        import verify_codebase_viz_health as v

        token = v.extract_session_token('x __HERMES_SESSION_TOKEN__="abc" y')
        errs = v.validate_health_body({"pygount_timeout_sec": 30, "plugin": "codebase-viz"})
        ok = (
            token == "abc"
            and bool(errs)
            and v.expected_pygount_timeout_sec() == 240
            and v.validate_health_body({"pygount_timeout_sec": 240, "plugin": "codebase-viz"}) == []
        )
        _step("verify_codebase_viz_health helpers", ok)
    finally:
        sys.path.pop(0)


def test_c5_manifest_version() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ok = data.get("version") == "2.5.0" and data.get("name") == "codebase-viz"
    _step("manifest 2.5.0", ok, data.get("version", "?"))


def test_c6_skip_launch_ps1() -> None:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
            "-RepoRoot",
            str(REPO),
            "-Quiet",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=90,
        env={**os.environ, "HERMES_SKIP_DASHBOARD_ON_START": "1"},
    )
    _step("PS1 skip start", proc.returncode == 0, f"exit={proc.returncode}")


def test_c7_pytest_unit_gate() -> None:
    py = Path.home() / "miniconda3/envs/hermes-env/python.exe"
    if not py.is_file():
        py = Path(sys.executable)
    targets = [
        "tests/plugins/test_codebase_viz_health_verify.py",
        "tests/windows/test_launch_dashboard_on_start.py",
    ]
    proc = subprocess.run(
        [str(py), "-m", "pytest", *targets, "-q", "--tb=short"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    _step("pytest unit gate", proc.returncode == 0, detail)


def main() -> int:
    print("=" * 60, flush=True)
    print("  Codebase Viz launch E2E - Audit", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_c1_launch_ps1_workspace_plugins()
    test_c2_start_hermes_no_default_browser_tab()
    test_c3_frontend_single_progress_bar()
    test_c4_verify_health_module()
    test_c5_manifest_version()
    test_c6_skip_launch_ps1()
    test_c7_pytest_unit_gate()

    print(flush=True)
    print("=" * 60, flush=True)
    if FAILURES == 0:
        print(f"  ALL PASS ({STEP}/{STEP})", flush=True)
    else:
        print(f"  FAILURES: {FAILURES}/{STEP}", file=sys.stderr, flush=True)
    print("=" * 60, flush=True)
    return 1 if FAILURES > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
