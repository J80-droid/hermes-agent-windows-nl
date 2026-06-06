#!/usr/bin/env python3
"""E2E: scorecard 10/10 regressie — Tier A clean, pytest helpers, RAG seed, RUN_AUDITS wiring."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

CONDA = Path.home() / "miniconda3/Scripts/conda.exe"


def _ps1_quote(path: Path | str) -> str:
    return str(path).replace("'", "''")


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


def test_e1_tier_a_pyproject_and_helpers() -> None:
    pyproject = _read("pyproject.toml")
    shell = _read("windows/HermesShellCommon.ps1")
    addopts_line = next(
        (ln for ln in pyproject.splitlines() if "addopts" in ln and "timeout-method" in ln),
        "",
    )
    ok = (
        "--timeout-method=signal" in addopts_line
        and "--timeout-method=thread" not in addopts_line
        and "function Invoke-HermesTierAPostAuditClean" in shell
        and "function Invoke-HermesTierASrcClean" in shell
        and "'run', '-n', $EnvName" in shell
        and "'--'" in shell
    )
    _step("pyproject signal + Tier A clean helpers", ok)


def test_e2_run_audits_skip_tier_a_flag() -> None:
    text = _read("windows/audits/RUN_AUDITS.ps1")
    ok = "SkipTierAPostClean" in text and "Invoke-HermesTierAPostAuditClean" in text
    _step("RUN_AUDITS SkipTierAPostClean + post-audit clean", ok)


def test_e3_preflight_skips_drift_gate() -> None:
    shell = _read("windows/HermesShellCommon.ps1")
    ok = "$Phase -eq 'Postflight'" in shell
    _step("drift gate only on Postflight phase", ok)


def test_e4_tier_a_src_clean_removes_marker() -> None:
    marker = REPO / "ui-tui" / "src" / "_scorecard_e2e_marker.tmp"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("leak", encoding="utf-8")
    shell = REPO / "windows" / "HermesShellCommon.ps1"
    ps = (
        f". '{_ps1_quote(shell)}'; "
        f"Invoke-HermesTierASrcClean -RepoRoot '{_ps1_quote(REPO)}'; "
        f"if (Test-Path '{_ps1_quote(marker)}') {{ exit 1 }} else {{ exit 0 }}"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO),
    )
    _step("Invoke-HermesTierASrcClean untracked leak", proc.returncode == 0, f"exit={proc.returncode}")


def test_e5_conda_audit_pytest_collect() -> None:
    if not CONDA.is_file():
        _step("Invoke-HermesCondaAuditPytest collect-only", True, "skip geen conda")
        return
    shell = REPO / "windows" / "HermesShellCommon.ps1"
    ps = (
        f". '{_ps1_quote(shell)}'; "
        f"Invoke-HermesCondaAuditPytest -CondaExe '{_ps1_quote(CONDA)}' "
        f"tests/windows/test_pytest_windows_timeout_policy.py --collect-only -q; "
        "exit $LASTEXITCODE"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "CondaValueError" not in combined
    _step("Invoke-HermesCondaAuditPytest collect-only", ok, f"exit={proc.returncode}")


def test_e6_audit_pytest_missing_python() -> None:
    shell = REPO / "windows" / "HermesShellCommon.ps1"
    ps = (
        f". '{_ps1_quote(shell)}'; "
        "Invoke-HermesAuditPytest -Python 'C:\\nonexistent\\hermes-missing-python.exe' "
        "tests/windows/test_pytest_windows_timeout_policy.py --collect-only -q; "
        "exit $LASTEXITCODE"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO),
    )
    _step("Invoke-HermesAuditPytest missing python exits 1", proc.returncode == 1, f"exit={proc.returncode}")


def test_e7_seed_whatif_no_copy() -> None:
    seed_ps = REPO / "windows/scripts/seed_rag_minimal_fixtures.ps1"
    with tempfile.TemporaryDirectory(prefix="hermes_seed_e2e_") as tmp:
        dest = Path(tmp) / "raw"
        dest.mkdir()
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(seed_ps),
                "-RepoRoot",
                str(REPO),
                "-DestRoot",
                str(dest),
                "-WhatIf",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO),
        )
        has_files = any(dest.rglob("*"))
        ok = proc.returncode == 0 and not has_files and "WhatIf" in (proc.stdout or "")
        _step("seed_rag_minimal_fixtures -WhatIf", ok, f"exit={proc.returncode}")


def test_e8_seed_to_temp_dest() -> None:
    seed_ps = REPO / "windows/scripts/seed_rag_minimal_fixtures.ps1"
    with tempfile.TemporaryDirectory(prefix="hermes_seed_e2e_") as tmp:
        dest = Path(tmp) / "raw"
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(seed_ps),
                "-RepoRoot",
                str(REPO),
                "-DestRoot",
                str(dest),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO),
        )
        smoke = dest / "01_Academics_Beta" / "smoke.md"
        ok = proc.returncode == 0 and smoke.is_file()
        _step("seed_rag_minimal_fixtures copy smoke.md", ok, f"exit={proc.returncode}")


def test_e9_run_tests_parallel_windows_timeout() -> None:
    text = _read("scripts/run_tests_parallel.py")
    ok = 'sys.platform == "win32"' in text and "PYTEST_ADDOPTS" in text and "timeout-method=thread" in text
    _step("run_tests_parallel Windows thread override", ok)


def main() -> int:
    print("=" * 60)
    print("  Scorecard 10/10 E2E")
    print("=" * 60)
    print()

    test_e1_tier_a_pyproject_and_helpers()
    test_e2_run_audits_skip_tier_a_flag()
    test_e3_preflight_skips_drift_gate()
    test_e4_tier_a_src_clean_removes_marker()
    test_e5_conda_audit_pytest_collect()
    test_e6_audit_pytest_missing_python()
    test_e7_seed_whatif_no_copy()
    test_e8_seed_to_temp_dest()
    test_e9_run_tests_parallel_windows_timeout()

    print()
    print("=" * 60)
    total = 9
    if FAILURES:
        print(f"  FAILURES: {FAILURES}/{total}")
        print("=" * 60)
        return 1
    print(f"  ALL PASS ({total}/{total})")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
