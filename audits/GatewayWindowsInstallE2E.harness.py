#!/usr/bin/env python3
"""E2E: Windows gateway login-install scripts (fork).

Scenario's:
  T1  Repo-artefacten (bat/ps1/py helpers)
  T2  VIRTUAL_ENV in gateway.cmd wijst naar venv-root (niet parent envs/)
  T3  gateway_pids_probe gebruikt all_profiles
  T4  refresh + elevated scripts importeerbaar
  T5  PS1 gebruikt dynamische task-naam (geen hardcoded core-only schtasks)
  T6  pytest subset (gateway_windows + fork script tests)

Draai: audits/RUN_GATEWAY_WINDOWS_INSTALL_E2E.bat
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] T{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] T{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_t1_repo_artefacts() -> None:
    required = [
        "windows/GATEWAY_INSTALL_LOGIN.bat",
        "windows/GATEWAY_INSTALL_LOGIN.ps1",
        "windows/GATEWAY_ENSURE_RUNNING.bat",
        "windows/GATEWAY_ENSURE_RUNNING.ps1",
        "windows/GATEWAY_STATUS.bat",
        "windows/scripts/GatewayWindowsCommon.ps1",
        "windows/scripts/gateway_install_login_elevated.py",
        "windows/scripts/gateway_refresh_task_script.py",
        "windows/scripts/gateway_pids_probe.py",
        "audits/RUN_GATEWAY_WINDOWS_INSTALL_E2E.bat",
    ]
    missing = [r for r in required if not (REPO / r).is_file()]
    _step("repo-artefacten gateway Windows install", not missing, ", ".join(missing) or "OK")


def test_t2_virtual_env_in_cmd_script() -> None:
    import re

    import hermes_cli.gateway_windows as gw

    content = gw._build_gateway_cmd_script(
        r"C:\miniconda3\envs\hermes-env\python.exe",
        r"C:\Users\me\AppData\Local\hermes\profiles\core",
        r"C:\Users\me\AppData\Local\hermes\profiles\core",
        "--profile core",
    )
    match = re.search(r'VIRTUAL_ENV=([^"\r\n]+)', content)
    venv = match.group(1) if match else ""
    ok = venv.endswith(r"hermes-env") and venv != r"C:\miniconda3\envs"
    _step("VIRTUAL_ENV wijst naar venv-root", ok, venv or "missing")


def test_t3_pids_probe_all_profiles() -> None:
    text = _read("windows/scripts/gateway_pids_probe.py")
    ok = "all_profiles=True" in text and "def main()" in text
    _step("gateway_pids_probe all_profiles + main()", ok)


def test_t4_helper_scripts_import() -> None:
    import importlib.util

    ok = True
    detail = ""
    for rel in (
        "windows/scripts/gateway_refresh_task_script.py",
        "windows/scripts/gateway_install_login_elevated.py",
        "windows/scripts/gateway_pids_probe.py",
    ):
        try:
            path = REPO / rel
            spec = importlib.util.spec_from_file_location(path.stem, path)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            assert hasattr(mod, "main")
        except Exception as exc:
            ok = False
            detail = f"{rel}: {exc}"
            break
    _step("helper scripts importeerbaar + main()", ok, detail)


def test_t5_ps1_dynamic_task_name() -> None:
    ensure = _read("windows/GATEWAY_ENSURE_RUNNING.ps1")
    common = _read("windows/scripts/GatewayWindowsCommon.ps1")
    ok = (
        "Resolve-HermesGatewayScheduledTaskName" in common
        and "schtasks /Run /TN $taskName" in ensure
        and "schtasks /Run /TN Hermes_Gateway_core" not in ensure
    )
    _step("PS1 dynamische Scheduled Task naam", ok)


def test_t6_pytest_subset() -> None:
    py = sys.executable
    proc = subprocess.run(
        [
            py,
            "-m",
            "pytest",
            "tests/hermes_cli/test_gateway_windows.py::test_gateway_cmd_script_uses_pythonw_without_replace_or_start_churn",
            "tests/hermes_cli/test_gateway_windows.py::test_build_gateway_cmd_script_virtual_env_points_to_venv_root",
            "tests/windows/test_gateway_windows_fork_scripts.py",
            "-q",
            "--tb=short",
            "-o",
            "addopts=--timeout=60 --timeout-method=thread",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    ok = proc.returncode == 0
    detail = (proc.stdout + proc.stderr).strip().splitlines()[-1] if not ok else "OK"
    _step("pytest gateway Windows subset", ok, detail)


def main() -> int:
    print("=== Gateway Windows Install E2E ===", flush=True)
    test_t1_repo_artefacts()
    test_t2_virtual_env_in_cmd_script()
    test_t3_pids_probe_all_profiles()
    test_t4_helper_scripts_import()
    test_t5_ps1_dynamic_task_name()
    test_t6_pytest_subset()
    if FAILURES:
        print(f"=== GATEWAY WINDOWS INSTALL E2E: FAIL ({FAILURES}) ===", file=sys.stderr, flush=True)
        return 1
    print("=== GATEWAY WINDOWS INSTALL E2E: PASS ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
