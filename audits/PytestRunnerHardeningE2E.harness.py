#!/usr/bin/env python3
"""E2E: pytest runner hardening (arg split, stderr exit, pipeline LASTEXITCODE).

Valideert fixes na upstream runner + Invoke-HermesAuditPytest stderr-gedrag.
Geen volledige pytest suite.
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

PS = [
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
]


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


def _run_ps(script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*PS, script],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO),
    )


def test_e1_get_pytest_args_function_present() -> None:
    text = _read("windows/scripts/Invoke-HermesPytestFromManifest.ps1")
    ok = "function Get-HermesPytestArgsFromConfig" in text and "function Build-HermesPytestArgsFromConfig" not in text
    _step("Get-HermesPytestArgsFromConfig (no legacy Build- name)", ok)


def test_e2_upstream_maxfail_junitxml_separate_args() -> None:
    helper = REPO / "audits" / "_PytestRunnerHardeningE2E_argcheck.ps1"
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(helper),
            str(REPO),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
    )
    ok = proc.returncode == 0
    detail = f"exit={proc.returncode}"
    if not ok:
        detail += " " + (proc.stderr or proc.stdout or "")[-180:].replace("\n", " ")
    _step("upstream maxfail/junitxml remain separate argv entries", ok, detail)


def test_e3_interpolation_upstream_extra_not_merged() -> None:
    script = """
    $maxfail = 50
    $junitPath = 'C:/tmp/junit.xml'
    $upstreamExtra = @(
        "--maxfail=$maxfail"
        "--junitxml=$junitPath"
    )
    if ($upstreamExtra.Count -ne 2) { exit 1 }
    if ($upstreamExtra[0] -ne '--maxfail=50') { exit 2 }
    if ($upstreamExtra[1] -ne '--junitxml=C:/tmp/junit.xml') { exit 3 }
    exit 0
    """
    proc = _run_ps(script)
    _step("PS @() upstreamExtra interpolation yields two elements", proc.returncode == 0, f"exit={proc.returncode}")


def test_e4_audit_pytest_stderr_continue() -> None:
    text = _read("windows/HermesShellCommon.ps1")
    ok = (
        "function Invoke-HermesAuditPytest" in text
        and "ErrorActionPreference = 'Continue'" in text
        and "Pytest schrijft teardown" in text
    )
    _step("Invoke-HermesAuditPytest Continue around native pytest", ok)


def test_e5_fork_gate_runner_global_lastexitcode() -> None:
    text = _read("windows/tests/RUN_PYTEST_FORK_GATE.ps1")
    ok = "$global:LASTEXITCODE" in text and "exit $gateExit" in text
    _step("RUN_PYTEST_FORK_GATE preserves global LASTEXITCODE after Tee-Object", ok)


def test_e6_upstream_runner_global_lastexitcode() -> None:
    text = _read("windows/tests/RUN_PYTEST_UPSTREAM.ps1")
    ok = "$global:LASTEXITCODE" in text and "exit $upstreamExit" in text
    _step("RUN_PYTEST_UPSTREAM preserves global LASTEXITCODE after Tee-Object", ok)


def test_e7_report_only_upstream_exit_zero() -> None:
    text = _read("windows/scripts/Invoke-HermesPytestFromManifest.ps1")
    ok = "if ($ReportOnly)" in text and "$global:LASTEXITCODE = 0" in text
    _step("Invoke-HermesPytestUpstream ReportOnly forces exit 0", ok)


def test_e8_drift_baseline_fork_intentional_section() -> None:
    text = _read("windows/scripts/Export-NousDriftBaseline.ps1")
    ok = "fork-intentional allowlist" in text and "Test-HermesPathTierAForkIntentional" in text
    _step("Export-NousDriftBaseline splits fork-intentional Tier A", ok)


def test_e9_production_gate_skip_rebuild_flag() -> None:
    text = _read("windows/audits/RUN_PRODUCTION_GATE.ps1")
    ok = "$skipRebuildTui" in text and "[switch]$SkipRebuildTui" in text
    _step("RUN_PRODUCTION_GATE SkipRebuildTui bound outside scriptblock", ok)


def test_e10_summarizer_skips_missing_junit_gracefully() -> None:
    text = _read("windows/scripts/Invoke-HermesPytestFromManifest.ps1")
    ok = "Test-Path -LiteralPath $junitPath" in text
    _step("upstream runner checks junit exists before summarize", ok)


def main() -> int:
    print("=" * 60)
    print("  Pytest runner hardening E2E")
    print("=" * 60)
    print()

    test_e1_get_pytest_args_function_present()
    test_e2_upstream_maxfail_junitxml_separate_args()
    test_e3_interpolation_upstream_extra_not_merged()
    test_e4_audit_pytest_stderr_continue()
    test_e5_fork_gate_runner_global_lastexitcode()
    test_e6_upstream_runner_global_lastexitcode()
    test_e7_report_only_upstream_exit_zero()
    test_e8_drift_baseline_fork_intentional_section()
    test_e9_production_gate_skip_rebuild_flag()
    test_e10_summarizer_skips_missing_junit_gracefully()

    print()
    print("=" * 60)
    total = 10
    if FAILURES:
        print(f"  FAILURES: {FAILURES}/{total}")
        print("=" * 60)
        return 1
    print(f"  ALL PASS ({total}/{total})")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
