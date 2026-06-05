#!/usr/bin/env python3
"""E2E: Codebase Viz productie (240s timeout, scan-status telemetry, launch wiring).

Geen live pygount op volledige repo — structurele checks op repo-artefacten.
Draai: audits/RUN_CODEBASE_VIZ_PRODUCTION_E2E.bat
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PLUGIN_API = REPO / "plugins/codebase-viz/dashboard/plugin_api.py"
PS1 = REPO / "windows/scripts/launch_dashboard_on_start.ps1"
RESTART_BAT = REPO / "audits/RESTART_CODEBASE_VIZ_DASHBOARD.bat"
VERIFY = REPO / "audits/verify_codebase_viz_health.py"
DIST_JS = REPO / "plugins/codebase-viz/dashboard/dist/index.js"
OPS = REPO / "docs/INSTITUTIONAL_OPERATIONS.md"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] P{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] P{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def test_p1_plugin_api_timeout_default_and_parser() -> None:
    text = PLUGIN_API.read_text(encoding="utf-8")
    ok = (
        '_parse_pygount_timeout' in text
        and 'PYGOUNT_TIMEOUT = _parse_pygount_timeout()' in text
        and "_parse_scan_mode" in text
        and 'CODEBASE_VIZ_SCAN_MODE = _parse_scan_mode()' in text
        and '"240"' in text
    )
    _step("plugin_api 240s + parser + scan_mode", ok)


def test_p2_scan_status_fields_in_source() -> None:
    text = PLUGIN_API.read_text(encoding="utf-8")
    fields = ["repo_path", "repo_label", "timeout_sec", "phase_label", "scan_mode", "refresh"]
    ok = all(f'"{f}"' in text for f in fields) and "_repo_scan_label" in text
    _step("scan-status telemetry fields", ok, ",".join(fields))


def test_p3_verify_env_aware() -> None:
    os.environ["CODEBASE_VIZ_PYGOUNT_TIMEOUT"] = "300"
    sys.path.insert(0, str(REPO / "audits"))
    try:
        import verify_codebase_viz_health as v

        ok = (
            v.expected_pygount_timeout_sec() == 300
            and v.validate_health_body({"pygount_timeout_sec": 300, "plugin": "codebase-viz"}) == []
            and v.validate_health_body({"pygount_timeout_sec": 240, "plugin": "codebase-viz"}) != []
        )
        _step("verify env-aware timeout", ok)
    finally:
        sys.path.pop(0)
        os.environ.pop("CODEBASE_VIZ_PYGOUNT_TIMEOUT", None)


def test_p4_dist_live_scan_ui() -> None:
    if not DIST_JS.is_file():
        _step("dist scan-target UI", False, "npm run build in dashboard/")
        return
    js = DIST_JS.read_text(encoding="utf-8", errors="replace")
    ok = "codebase-viz-scan-target" in js and "max " in js
    _step("dist scan-target + max elapsed", ok)


def test_p5_launch_ps1_production_wiring() -> None:
    ps1 = PS1.read_text(encoding="utf-8")
    checks = [
        "'240'" in ps1 or '"240"' in ps1,
        "Import-HermesPythonPolicy" in ps1,
        "pip install pygount" in ps1,
        "Test-CodebaseVizHealth" in ps1,
        "verify_codebase_viz_health.py" in ps1,
        "Remove-Item Env:CODEBASE_VIZ_PYGOUNT_TIMEOUT" in ps1,
    ]
    _step("launch PS1 productie", all(checks), f"{sum(checks)}/{len(checks)}")


def test_p6_restart_bat() -> None:
    bat = RESTART_BAT.read_text(encoding="utf-8")
    ok = "CODEBASE_VIZ_PYGOUNT_TIMEOUT=240" in bat and "pip install pygount" in bat
    _step("RESTART bat 240 + pygount", ok)


def test_p7_institutional_ops_section() -> None:
    ops = OPS.read_text(encoding="utf-8")
    ok = (
        "### Codebase Viz (dashboard-plugin)" in ops
        and "pygount_timeout_sec=240" in ops
        and "RESTART_CODEBASE_VIZ_DASHBOARD.bat" in ops
    )
    _step("INSTITUTIONAL_OPERATIONS sectie", ok)


def test_p8_pytest_production_unit_gate() -> None:
    py = Path.home() / "miniconda3/envs/hermes-env/python.exe"
    if not py.is_file():
        py = Path(sys.executable)
    proc = subprocess.run(
        [
            str(py),
            "-m",
            "pytest",
            "tests/plugins/test_codebase_viz_plugin.py",
            "-q",
            "--tb=line",
            "-k",
            "scan_status or pygount_timeout or repo_scan or scan_start",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    detail = tail[-1] if tail else f"exit={proc.returncode}"
    _step("pytest productie subset", proc.returncode == 0, detail)


def main() -> int:
    print("=" * 60, flush=True)
    print("  Codebase Viz production E2E", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    test_p1_plugin_api_timeout_default_and_parser()
    test_p2_scan_status_fields_in_source()
    test_p3_verify_env_aware()
    test_p4_dist_live_scan_ui()
    test_p5_launch_ps1_production_wiring()
    test_p6_restart_bat()
    test_p7_institutional_ops_section()
    test_p8_pytest_production_unit_gate()

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
