#!/usr/bin/env python3
"""E2E: pytest audit-env hardening (PYTEST_ADDOPTS, institutional gate wiring).

Valideert dat audit-pytest niet crasht op dubbele pytest_timeout-registratie en dat
RAG MCP-sync overlay bootstrap gebruikt. Geen live netwerk.
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

AUDIT_PYTEST_ARGS = ("-o", "addopts=--timeout=30 --timeout-method=thread")
PROBE_TEST = "tests/windows/test_hermes_python_institutional.py"


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


def _run_pytest(
    extra_args: list[str],
    *,
    env: dict[str, str] | None = None,
    collect_only: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [str(PY), "-m", "pytest", PROBE_TEST]
    if collect_only:
        cmd.append("--collect-only")
    cmd.extend(["-q", "--tb=line"])
    cmd.extend(extra_args)
    run_env = os.environ.copy()
    if env is not None:
        run_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
        env=run_env,
    )


def test_e1_shell_common_helpers_documented() -> None:
    text = _read("windows/HermesShellCommon.ps1")
    ok = (
        "function Clear-HermesPytestAddoptsForAudit" in text
        and "function Get-HermesAuditPytestOverrideArgs" in text
    )
    if "if (-not $env:PYTEST_ADDOPTS)" in text:
        default_block = text.split("if (-not $env:PYTEST_ADDOPTS)", 1)[1].split("function ", 1)[0]
        ok = ok and "-p pytest_timeout" not in default_block
    _step("HermesShellCommon audit pytest helpers", ok)


def test_e2_double_timeout_plugin_fails_without_clear() -> None:
    """Reproduce regressie: -p pytest_timeout + pyproject timeout = exit 3/4."""
    proc = _run_pytest(
        [],
        env={"PYTEST_ADDOPTS": "-p pytest_timeout --timeout=30 --timeout-method=thread"},
    )
    err = (proc.stderr or proc.stdout or "").lower()
    ok = proc.returncode != 0 and (
        "plugin already registered" in err or "pytest_timeout" in err or proc.returncode in (3, 4)
    )
    _step(
        "PYTEST_ADDOPTS -p pytest_timeout breaks collect",
        ok,
        f"exit={proc.returncode}",
    )


def test_e3_audit_env_collect_succeeds() -> None:
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    proc = _run_pytest(list(AUDIT_PYTEST_ARGS), env=env)
    ok = proc.returncode == 0
    detail = f"exit={proc.returncode}"
    if not ok:
        tail = (proc.stderr or proc.stdout or "")[-400:].replace("\n", " ")
        detail = f"{detail} {tail}"
    _step("cleared PYTEST_ADDOPTS + audit override collects", ok, detail)


def test_e4_sync_mcp_check_imports_overlay() -> None:
    script = REPO / "scripts/rag_pipeline/sync_profile_mcp_from_domains.py"
    proc = subprocess.run(
        [str(PY), str(script), "--check"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    err = proc.stderr or proc.stdout or ""
    ok = proc.returncode in (0, 1) and "profile_mcp_format" not in err
    ok = ok and "ModuleNotFoundError" not in err
    _step("sync_profile_mcp_from_domains --check (no import error)", ok, f"exit={proc.returncode}")


def test_e5_institutional_p0_p1_update_knowledge_path() -> None:
    bat = _read("windows/scripts/institutional_p0_p1.bat")
    ok = (
        "INST_SCRIPT_DIR=%~dp0" in bat
        and "UPDATE_KNOWLEDGE_BAT=%INST_SCRIPT_DIR%update_knowledge.bat" in bat
    )
    target = REPO / "windows" / "scripts" / "update_knowledge.bat"
    _step(
        "institutional_p0_p1 UPDATE_KNOWLEDGE_BAT",
        ok and target.is_file(),
        str(target.name),
    )


def test_e6_production_gate_clears_pytest_addopts() -> None:
    gate = _read("windows/audits/RUN_INSTITUTIONAL_PRODUCTION_GATE.ps1")
    ok = "Clear-HermesPytestAddoptsForAudit" in gate
    _step("RUN_INSTITUTIONAL_PRODUCTION_GATE clears PYTEST_ADDOPTS", ok)


def test_e7_e2e_cores_use_audit_pytest_helpers() -> None:
    cores = [
        "windows/audits/HermesPythonInstitutionalE2E.core.ps1",
        "windows/audits/KnowledgeRepositoryE2E.core.ps1",
    ]
    ok = all(
        "Clear-HermesPytestAddoptsForAudit" in _read(c)
        and "Get-HermesAuditPytestOverrideArgs" in _read(c)
        for c in cores
    )
    _step("institutional E2E cores use audit pytest helpers", ok)


def test_e8_hardening_h9_clears_pytest_addopts() -> None:
    harness = _read("audits/InstitutionalHardeningE2E.harness.py")
    ok = 'env.pop("PYTEST_ADDOPTS", None)' in harness and "addopts=--timeout=30" in harness
    _step("InstitutionalHardening H9 pytest env isolation", ok)


def main() -> int:
    print("=" * 60)
    print("  Pytest audit-env E2E")
    print("=" * 60)
    print()

    test_e1_shell_common_helpers_documented()
    test_e2_double_timeout_plugin_fails_without_clear()
    test_e3_audit_env_collect_succeeds()
    test_e4_sync_mcp_check_imports_overlay()
    test_e5_institutional_p0_p1_update_knowledge_path()
    test_e6_production_gate_clears_pytest_addopts()
    test_e7_e2e_cores_use_audit_pytest_helpers()
    test_e8_hardening_h9_clears_pytest_addopts()

    print()
    print("=" * 60)
    if FAILURES:
        print(f"  FAILURES: {FAILURES}/8")
        print("=" * 60)
        return 1
    print("  ALL PASS (8/8)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
