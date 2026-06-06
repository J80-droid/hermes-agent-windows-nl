#!/usr/bin/env python3
"""E2E: toolset dashboard post-setup overlay (Tier B wiring + bootstrap).

Scenario's:
  T1  Repo-artefacten (overlay patches + web UI + tests)
  T2  bootstrap.py registreert web_server_fork_patch
  T3  Routes na install() (env + post-setup + action log)
  T4  Dubbele apply_web_server_fork_patch = idempotent (geen dubbele routes)
  T5  tools_config helpers na bootstrap
  T6  argparse post-setup late inject (geen upstream conflict)
  T7  overlay web: Drawer + toolsetDashboardApi + SkillsPage
  T8  pytest overlay subset (post-setup + web_server fork)
  T9  fork gates harness bevat geen post-setup parser conflict

Draai: audits/RUN_TOOLSET_DASHBOARD_E2E.bat
"""

from __future__ import annotations

import argparse
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
        "overlay/hermes_cli/web_server_fork_patch.py",
        "overlay/hermes_cli/tools_config_fork_patch.py",
        "overlay/hermes_cli/argparse_fork_patch.py",
        "overlay/web/src/components/ToolsetConfigDrawer.tsx",
        "overlay/web/src/lib/toolsetDashboardApi.ts",
        "overlay/web/src/pages/SkillsPage.tsx",
        "tests/overlay/test_tools_config_post_setup_fork.py",
        "tests/overlay/test_web_server_toolset_fork_patch.py",
        "audits/RUN_TOOLSET_DASHBOARD_E2E.bat",
    ]
    missing = [r for r in required if not (REPO / r).is_file()]
    _step("repo-artefacten overlay toolset dashboard", not missing, ", ".join(missing) or "OK")


def test_t2_bootstrap_registers_patch() -> None:
    text = _read("overlay/bootstrap.py")
    ok = (
        "web_server_fork_patch" in text
        and "apply_web_server_fork_patch" in text
        and "apply_tools_config_fork_patch" in text
    )
    _step("bootstrap registreert web_server + tools_config patches", ok)


def test_t3_routes_after_install() -> None:
    sys.path.insert(0, str(REPO))
    from overlay.bootstrap import install

    install()
    from hermes_cli import web_server as ws

    paths = {getattr(r, "path", "") for r in ws.app.routes}
    ok = (
        "/api/tools/toolsets/{name}/env" in paths
        and "/api/tools/toolsets/{name}/post-setup" in paths
        and ws._ACTION_LOG_FILES.get("tools-post-setup") == "action-tools-post-setup.log"
    )
    _step("routes + action log na install()", ok)


def test_t4_web_server_patch_idempotent() -> None:
    sys.path.insert(0, str(REPO))
    from overlay.bootstrap import install
    from overlay.hermes_cli.web_server_fork_patch import apply_web_server_fork_patch

    install()
    from hermes_cli import web_server as ws

    before = len(ws.app.routes)
    apply_web_server_fork_patch()
    apply_web_server_fork_patch()
    after = len(ws.app.routes)
    env_count = sum(
        1 for r in ws.app.routes if getattr(r, "path", "") == "/api/tools/toolsets/{name}/env"
    )
    ok = after == before and env_count <= 1
    _step("web_server_fork_patch idempotent", ok, f"routes={after} env_routes={env_count}")


def test_t5_tools_config_helpers() -> None:
    sys.path.insert(0, str(REPO))
    from overlay.bootstrap import install

    install()
    import hermes_cli.tools_config as tc

    ok = callable(getattr(tc, "valid_post_setup_keys", None)) and callable(
        getattr(tc, "run_post_setup_command", None)
    )
    keys = tc.valid_post_setup_keys() if ok else set()
    _step("tools_config post-setup helpers", ok, f"{len(keys)} keys")


def test_t6_argparse_late_post_setup() -> None:
    from overlay.hermes_cli.argparse_fork_patch import apply_argparse_fork_patch

    apply_argparse_fork_patch()
    root = argparse.ArgumentParser()
    tools = root.add_subparsers(dest="tools_command")
    sub = tools.add_parser("tools")
    action = sub.add_subparsers(dest="tools_action")
    action.add_parser("list")
    action.add_parser("disable")
    action.add_parser("enable")

    def cmd_tools(_a):
        return 0

    sub.set_defaults(func=cmd_tools)
    ok = "post-setup" in action.choices and len(action.choices) == 4
    _step("argparse late inject post-setup (upstream-safe)", ok)


def test_t7_overlay_web_wiring() -> None:
    drawer = _read("overlay/web/src/components/ToolsetConfigDrawer.tsx")
    api = _read("overlay/web/src/lib/toolsetDashboardApi.ts")
    page = _read("overlay/web/src/pages/SkillsPage.tsx")
    ok = (
        "toolsetDashboardApi" in drawer
        and "saveToolsetEnv" in api
        and "runToolsetPostSetup" in api
        and "ToolsetConfigDrawer" in page
        and "Configure" in page
    )
    _step("overlay web Drawer + API + SkillsPage", ok)


def test_t8_pytest_overlay_subset() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/overlay/test_tools_config_post_setup_fork.py",
            "tests/overlay/test_web_server_toolset_fork_patch.py",
            "-q",
            "--tb=line",
            "-o",
            "addopts=--timeout=60 --timeout-method=thread",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [""]
    _step("pytest overlay toolset subset", ok, tail[0][:120])


def test_t9_fork_gates_no_early_post_setup() -> None:
    text = _read("overlay/hermes_cli/argparse_fork_patch.py")
    ok = "_inject_tools_post_setup_late" in text and "name != \"post-setup\"" not in text.replace(
        "elif dest == \"tools_action\" and name == \"post-setup\":", ""
    )
    # Must use late inject, not eager _ensure on every tools_action parser add.
    ok = ok and "_inject_tools_post_setup_late" in text and "if name != \"post-setup\":" not in text
    _step("argparse geen eager post-setup (upstream-safe)", ok)


def main() -> int:
    print("=== Toolset Dashboard Post-Setup E2E ===", flush=True)
    test_t1_repo_artefacts()
    test_t2_bootstrap_registers_patch()
    test_t3_routes_after_install()
    test_t4_web_server_patch_idempotent()
    test_t5_tools_config_helpers()
    test_t6_argparse_late_post_setup()
    test_t7_overlay_web_wiring()
    test_t8_pytest_overlay_subset()
    test_t9_fork_gates_no_early_post_setup()
    if FAILURES:
        print(f"\n=== TOOLSET DASHBOARD E2E: FAIL ({FAILURES}) ===", file=sys.stderr, flush=True)
        return 1
    print("\n=== TOOLSET DASHBOARD E2E: PASS ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
