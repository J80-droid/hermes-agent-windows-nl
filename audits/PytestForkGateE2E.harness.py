#!/usr/bin/env python3
"""E2E: pytest fork gate manifest + runner wiring (geen volledige pytest suite).

Valideert SSOT manifest, loader JSON, PowerShell runners, RUN_AUDITS preflight en
upstream summary helper. Geen live netwerk.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

LOADER = REPO / "windows/scripts/load_pytest_fork_gate.py"
MANIFEST = REPO / "windows/tests/pytest_fork_gate.yaml"
SUMMARIZER = REPO / "windows/scripts/summarize_pytest_junit.py"
AUDIT_OVERRIDE = ("-o", "addopts=--timeout=30 --timeout-method=thread")


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


def _run_loader(mode: str, repo_root: Path | None = None) -> subprocess.CompletedProcess[str]:
    args = [str(PY), str(LOADER), "--mode", mode]
    if repo_root is not None:
        args.extend(["--repo-root", str(repo_root)])
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO),
    )


def test_e1_manifest_exists_and_documents_e2e_exclusions() -> None:
    text = _read("windows/tests/pytest_fork_gate.yaml")
    ok = (
        MANIFEST.is_file()
        and "version: 1" in text
        and "tests/overlay/" in text
        and "test_nous_overlay_fork_gates_e2e_harness_runs" in text
        and "test_repo_hygiene_institutional_e2e" in text
    )
    _step("pytest_fork_gate.yaml SSOT + e2e exclusion docs", ok)


def test_e2_loader_gate_mode_json() -> None:
    proc = _run_loader("gate", REPO)
    ok = proc.returncode == 0
    detail = f"exit={proc.returncode}"
    if ok:
        try:
            payload = json.loads(proc.stdout)
            ok = (
                payload.get("mode") == "gate"
                and isinstance(payload.get("paths"), list)
                and payload.get("paths")
                and "not e2e" in str(payload.get("markers", ""))
            )
        except json.JSONDecodeError:
            ok = False
            detail = "invalid json"
    else:
        detail = (proc.stderr or proc.stdout or detail)[-200:]
    _step("load_pytest_fork_gate --mode gate", ok, detail)


def test_e3_loader_upstream_mode_json() -> None:
    proc = _run_loader("upstream", REPO)
    ok = proc.returncode == 0
    detail = f"exit={proc.returncode}"
    if ok:
        try:
            payload = json.loads(proc.stdout)
            ok = payload.get("mode") == "upstream" and int(payload.get("maxfail", 0)) >= 1
        except json.JSONDecodeError:
            ok = False
            detail = "invalid json"
    _step("load_pytest_fork_gate --mode upstream", ok, detail)


def test_e4_loader_fails_on_missing_gate_path(tmp_path: Path) -> None:
    work = tmp_path / f"loader_e2e_{uuid.uuid4().hex}"
    mini = work / "mini"
    (mini / "windows" / "tests").mkdir(parents=True, exist_ok=True)
    (mini / "windows" / "scripts").mkdir(parents=True, exist_ok=True)
    (mini / "windows" / "scripts" / "load_pytest_fork_gate.py").write_text(
        LOADER.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (mini / "windows" / "tests" / "pytest_fork_gate.yaml").write_text(
        textwrap.dedent(
            """
            version: 1
            markers: "not e2e"
            paths:
              - tests/does_not_exist.py
            ignores: []
            upstream:
              paths: [tests/]
              ignores: []
              maxfail_default: 50
              junit: windows/tests/pytest_upstream_junit.xml
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    proc = _run_loader("gate", mini)
    ok = proc.returncode != 0 and "missing" in (proc.stderr or proc.stdout).lower()
    _step("loader exit 1 on missing gate path", ok, f"exit={proc.returncode}")


def test_e5_shared_runner_functions_present() -> None:
    text = _read("windows/scripts/Invoke-HermesPytestFromManifest.ps1")
    ok = all(
        needle in text
        for needle in (
            "function Invoke-HermesPytestGate",
            "function Invoke-HermesPytestUpstream",
            "function Get-HermesPytestForkGateConfig",
            "function Get-HermesPytestArgsFromConfig",
            "Get-HermesAuditPython",
            "Invoke-HermesAuditPytest",
        )
    )
    _step("Invoke-HermesPytestFromManifest.ps1 helpers", ok)


def test_e6_run_audits_preflight_uses_fork_gate() -> None:
    text = _read("windows/audits/RUN_AUDITS.ps1")
    ok = "pytest-fork-gate" in text and "RUN_PYTEST_FORK_GATE" in text
    bad = "pytest-overlay" in text or "pytest-profile-subset" in text
    _step("RUN_AUDITS preflight pytest-fork-gate (no legacy steps)", ok and not bad)


def test_e7_production_gate_skips_duplicate_pytest() -> None:
    text = _read("windows/audits/RUN_PRODUCTION_GATE.ps1")
    ok = (
        "RUN_PYTEST_FORK_GATE" in text
        and "-SkipPytest" in text
        and "Start-Transcript" in text
    )
    _step("RUN_PRODUCTION_GATE fork gate + SkipPytest + transcript", ok)


def test_e8_run_pytest_shim_default_fork_gate() -> None:
    text = _read("windows/tests/RUN_PYTEST.ps1")
    ok = "RUN_PYTEST_FORK_GATE" in text and "-Upstream" in text
    _step("RUN_PYTEST.ps1 shim default fork gate", ok)


def test_e9_audit_pytest_override_thread() -> None:
    text = _read("windows/HermesShellCommon.ps1")
    ok = "Get-HermesAuditPytestOverrideArgs" in text and "--timeout-method=thread" in text
    _step("Get-HermesAuditPytestOverrideArgs thread override", ok)


def _write_sample_junit(path: Path) -> None:
    suite = ET.Element("testsuite")
    for file_name, test_name, tag in (
        ("tests/foo/test_bar.py", "test_fail", "failure"),
        ("tests/foo/test_bar.py", "test_known", "failure"),
        ("tests/foo/test_bar.py", "test_ok", None),
    ):
        case = ET.SubElement(suite, "testcase", {"file": file_name, "name": test_name})
        if tag:
            ET.SubElement(case, tag, {"message": tag})
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def test_e10_summarize_junit_known_vs_new(tmp_path: Path) -> None:
    work = tmp_path / f"summarize_e2e_{uuid.uuid4().hex}"
    work.mkdir(parents=True, exist_ok=True)
    junit = work / "sample.xml"
    _write_sample_junit(junit)

    known = work / "known.txt"
    known.write_text("# comment\n tests/foo/test_bar.py::test_known \n", encoding="utf-8")
    out = work / "summary.json"
    proc = subprocess.run(
        [
            str(PY),
            str(SUMMARIZER),
            "--junit",
            str(junit),
            "--output",
            str(out),
            "--known-fails",
            str(known),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO),
    )
    ok = proc.returncode == 0 and out.is_file()
    if ok:
        payload = json.loads(out.read_text(encoding="utf-8"))
        ok = payload["failed"] == 2 and payload["new_failures_count"] == 1 and payload["passed"] == 1
    _step("summarize_pytest_junit known vs new failures", ok, f"exit={proc.returncode}")


def test_e11_manifest_path_collect_only() -> None:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    proc = subprocess.run(
        [
            str(PY),
            "-m",
            "pytest",
            "tests/overlay/test_doctor_fork_patch.py",
            "--collect-only",
            "-q",
            "--tb=line",
            *AUDIT_OVERRIDE,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
        env=env,
    )
    ok = proc.returncode == 0
    detail = f"exit={proc.returncode}"
    if not ok:
        detail += " " + (proc.stderr or proc.stdout or "")[-200:].replace("\n", " ")
    _step("manifest overlay path collect-only (thread)", ok, detail)


def main() -> int:
    print("=" * 60)
    print("  Pytest fork gate E2E")
    print("=" * 60)
    print()

    test_e1_manifest_exists_and_documents_e2e_exclusions()
    test_e2_loader_gate_mode_json()
    test_e3_loader_upstream_mode_json()
    test_e4_loader_fails_on_missing_gate_path(Path(os.environ.get("TEMP", "/tmp")))
    test_e5_shared_runner_functions_present()
    test_e6_run_audits_preflight_uses_fork_gate()
    test_e7_production_gate_skips_duplicate_pytest()
    test_e8_run_pytest_shim_default_fork_gate()
    test_e9_audit_pytest_override_thread()
    test_e10_summarize_junit_known_vs_new(Path(os.environ.get("TEMP", "/tmp")))
    test_e11_manifest_path_collect_only()

    print()
    print("=" * 60)
    total = 11
    if FAILURES:
        print(f"  FAILURES: {FAILURES}/{total}")
        print("=" * 60)
        return 1
    print(f"  ALL PASS ({total}/{total})")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
