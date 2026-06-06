#!/usr/bin/env python3
"""E2E: toolset dashboard (Tier A upstream + fork MCP sentinel overlay).

Scenario's:
  T1  Tier A artefacten (Drawer, api.ts, web_server routes, main post-setup)
  T2  bootstrap registreert tools_config_fork_patch (geen web_server overlay)
  T3  Routes na install() (env + post-setup + action log)
  T4  Geen overlay web_server_fork_patch (lean Pad 1)
  T5  tools_config post-setup helpers (Tier A)
  T6  main.py post-setup subparser (Tier A)
  T7  Tier A web wiring (Drawer + api + SkillsPage)
  T8  pytest subset (fork patch + upstream dashboard tests)
  T9  argparse overlay zonder post-setup inject (upstream-safe)

Draai: audits/RUN_TOOLSET_DASHBOARD_E2E.bat
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
        "web/src/components/ToolsetConfigDrawer.tsx",
        "web/src/lib/api.ts",
        "web/src/pages/SkillsPage.tsx",
        "hermes_cli/web_server.py",
        "hermes_cli/main.py",
        "overlay/hermes_cli/tools_config_fork_patch.py",
        "tests/overlay/test_tools_config_fork_patch.py",
        "audits/RUN_TOOLSET_DASHBOARD_E2E.bat",
    ]
    absent_overlay = [
        "overlay/hermes_cli/web_server_fork_patch.py",
        "overlay/web/src/components/ToolsetConfigDrawer.tsx",
        "overlay/web/src/lib/toolsetDashboardApi.ts",
        "overlay/web/src/pages/SkillsPage.tsx",
    ]
    missing = [r for r in required if not (REPO / r).is_file()]
    stale = [r for r in absent_overlay if (REPO / r).is_file()]
    ok = not missing and not stale
    detail = ", ".join(missing + [f"stale:{s}" for s in stale]) or "OK"
    _step("repo-artefacten Tier A toolset dashboard", ok, detail)


def test_t2_bootstrap_registers_patch() -> None:
    text = _read("overlay/bootstrap.py")
    ok = (
        "apply_tools_config_fork_patch" in text
        and "web_server_fork_patch" not in text
        and "apply_web_server_fork_patch" not in text
    )
    _step("bootstrap tools_config fork only (lean)", ok)


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


def test_t4_no_overlay_web_server_patch() -> None:
    ok = not (REPO / "overlay/hermes_cli/web_server_fork_patch.py").is_file()
    _step("geen overlay web_server_fork_patch", ok)


def test_t5_tools_config_helpers() -> None:
    sys.path.insert(0, str(REPO))
    from overlay.bootstrap import install

    install()
    import hermes_cli.tools_config as tc

    ok = callable(getattr(tc, "valid_post_setup_keys", None)) and callable(
        getattr(tc, "run_post_setup_command", None)
    )
    keys = tc.valid_post_setup_keys() if ok else set()
    _step("tools_config post-setup helpers (Tier A)", ok, f"{len(keys)} keys")


def test_t6_main_post_setup_parser() -> None:
    text = _read("hermes_cli/main.py")
    ok = '"post-setup"' in text and "run_post_setup_command" in text
    _step("main.py post-setup subparser (Tier A)", ok)


def test_t7_tier_a_web_wiring() -> None:
    drawer = _read("web/src/components/ToolsetConfigDrawer.tsx")
    api = _read("web/src/lib/api.ts")
    page = _read("web/src/pages/SkillsPage.tsx")
    ok = (
        "saveToolsetEnv" in api
        and "runToolsetPostSetup" in api
        and "ToolsetConfigDrawer" in page
        and "Configure" in page
        and "api.saveToolsetEnv" in drawer or "api.runToolsetPostSetup" in drawer
    )
    _step("Tier A web Drawer + api + SkillsPage", ok)


def test_t8_pytest_subset() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/overlay/test_tools_config_fork_patch.py",
            "tests/hermes_cli/test_dashboard_admin_endpoints.py",
            "-q",
            "--tb=line",
            "-k",
            "toolset or post_setup or expand_cli or Toolset",
            "-o",
            "addopts=",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    ok = proc.returncode == 0
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [""]
    _step("pytest toolset subset", ok, tail[0][:120])


def test_t9_argparse_no_overlay_post_setup() -> None:
    text = _read("overlay/hermes_cli/argparse_fork_patch.py")
    ok = (
        "_inject_tools_post_setup_late" not in text
        and "_wrap_cmd_tools_handler" not in text
        and "post-setup" not in text
    )
    _step("argparse overlay zonder post-setup (upstream-safe)", ok)


def main() -> int:
    print("=== Toolset Dashboard E2E (Tier A) ===", flush=True)
    test_t1_repo_artefacts()
    test_t2_bootstrap_registers_patch()
    test_t3_routes_after_install()
    test_t4_no_overlay_web_server_patch()
    test_t5_tools_config_helpers()
    test_t6_main_post_setup_parser()
    test_t7_tier_a_web_wiring()
    test_t8_pytest_subset()
    test_t9_argparse_no_overlay_post_setup()
    if FAILURES:
        print(f"\n=== TOOLSET DASHBOARD E2E: FAIL ({FAILURES}) ===", file=sys.stderr, flush=True)
        return 1
    print("\n=== TOOLSET DASHBOARD E2E: PASS ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
