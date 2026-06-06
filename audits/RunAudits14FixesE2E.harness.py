#!/usr/bin/env python3
"""E2E: RUN_AUDITS 14-fixes regressie (config-drift, pytest thread, YOLO width).

Valideert wiring en gedrag van de drie root-cause fixes zonder volledige RUN_AUDITS (~24 min).
Geen live netwerk.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def test_e1_pyproject_uses_thread_timeout() -> None:
    text = _read("pyproject.toml")
    ok = "--timeout-method=thread" in text and "--timeout-method=signal" not in text
    _step("pyproject.toml timeout-method=thread", ok)


def test_e2_strip_script_bootstraps_overlay() -> None:
    text = _read("windows/scripts/strip_profile_global_config_blocks.py")
    ok = (
        "from overlay.bootstrap import install" in text
        and "install()" in text
        and "profile_model_inheritance" in text
    )
    _step("strip_profile_global_config_blocks overlay bootstrap", ok)


def test_e3_doctor_fork_patch_strip_on_fix() -> None:
    text = _read("overlay/hermes_cli/doctor_fork_patch.py")
    ok = (
        "def check_profile_global_config_blocks" in text
        and "strip_all_profile_global_blocks" in text
        and "_run_fork_doctor_checks" in text
        and "run_doctor_patched" in text
    )
    _step("doctor_fork_patch global-blocks + run_doctor wrapper", ok)


def test_e4_shell_common_audit_pytest_helpers() -> None:
    text = _read("windows/HermesShellCommon.ps1")
    ok = (
        "function Invoke-HermesAuditPytest" in text
        and "function Invoke-HermesCondaAuditPytest" in text
        and "Clear-HermesPytestAddoptsForAudit" in text
        and "Get-HermesAuditPytestOverrideArgs" in text
    )
    _step("HermesShellCommon Invoke-HermesAuditPytest helpers", ok)


def test_e5_run_audits_preflight_strip() -> None:
    text = _read("windows/audits/RUN_AUDITS.ps1")
    ok = (
        "preflight_strip_profile_global_blocks" in text
        and "strip_profile_global_config_blocks.py" in text
        and "$IncludeAllE2E" in text
    )
    _step("RUN_AUDITS IncludeAllE2E preflight strip", ok)


def test_e6_pytest_collect_no_sigalrm() -> None:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    proc = subprocess.run(
        [
            str(PY),
            "-m",
            "pytest",
            "tests/windows/test_critical_windows_scripts.py",
            "--collect-only",
            "-q",
            "--tb=line",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
        env=env,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "signal only works" not in combined.lower()
    _step("pytest collect critical windows (no SIGALRM)", ok, f"exit={proc.returncode}")


def test_e7_status_bar_width_test_disables_yolo() -> None:
    text = _read("tests/cli/test_cli_status_bar.py")
    ok = "_is_session_yolo_active = lambda: False" in text
    _step("TestStatusBarWidthSource disables YOLO badge", ok)


def test_e8_audit_scripts_migrated_sample() -> None:
    samples = [
        "windows/audits/RUN_IDE_MAINTENANCE_E2E.ps1",
        "windows/audits/RUN_PROFILE_SWITCH_E2E.ps1",
        "windows/audits/TrustForensicE2E.core.ps1",
    ]
    ok = all("Invoke-HermesAuditPytest" in _read(p) or "Invoke-HermesCondaAuditPytest" in _read(p) for p in samples)
    _step("sample audit scripts use audit pytest helpers", ok)


def test_e9_strip_script_runs() -> None:
    proc = subprocess.run(
        [str(PY), str(REPO / "windows/scripts/strip_profile_global_config_blocks.py")],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "[OK]" in combined
    _step("strip_profile_global_config_blocks.py runtime", ok, f"exit={proc.returncode}")


def test_e10_doctor_fork_patch_unit_import() -> None:
    proc = subprocess.run(
        [
            str(PY),
            "-m",
            "pytest",
            "tests/overlay/test_doctor_fork_patch.py",
            "-q",
            "--tb=line",
            "-o",
            "addopts=--timeout=30 --timeout-method=thread",
        ],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(REPO),
        env={k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"},
    )
    ok = proc.returncode == 0
    detail = f"exit={proc.returncode}"
    if not ok:
        detail += " " + (proc.stderr or proc.stdout or "")[-200:].replace("\n", " ")
    _step("unit tests overlay/test_doctor_fork_patch.py", ok, detail)


def main() -> int:
    print("=" * 60)
    print("  RUN_AUDITS 14-fixes E2E")
    print("=" * 60)
    print()

    test_e1_pyproject_uses_thread_timeout()
    test_e2_strip_script_bootstraps_overlay()
    test_e3_doctor_fork_patch_strip_on_fix()
    test_e4_shell_common_audit_pytest_helpers()
    test_e5_run_audits_preflight_strip()
    test_e6_pytest_collect_no_sigalrm()
    test_e7_status_bar_width_test_disables_yolo()
    test_e8_audit_scripts_migrated_sample()
    test_e9_strip_script_runs()
    test_e10_doctor_fork_patch_unit_import()

    print()
    print("=" * 60)
    if FAILURES:
        print(f"  FAILURES: {FAILURES}/10")
        print("=" * 60)
        return 1
    print("  ALL PASS (10/10)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
