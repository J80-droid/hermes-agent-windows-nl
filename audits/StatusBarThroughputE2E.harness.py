#!/usr/bin/env python3
"""E2E: status bar tokens/s (classic CLI + formatter + TUI parity).

No live API, no PTY. Covers throughput modules, cli hooks, agent finalize,
gateway config RPC, and unit-test gates.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0
STEP = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_e1_repo_artefacts() -> None:
    required = [
        "overlay/hermes_cli/status_bar_throughput.py",
        "overlay/hermes_cli/cli_tps_command.py",
        "overlay/hermes_cli/cli_tps_stream_hooks.py",
        "overlay/hermes_cli/cli_fork_patch.py",
        "overlay/hermes_cli/cli_command_patches.py",
        "overlay/agent/agent_throughput_fork_patch.py",
        "overlay/ui-tui/src/domain/statusBarThroughput.ts",
        "cli.py",
        "run_agent.py",
        "agent/conversation_loop.py",
        "tests/hermes_cli/test_status_bar_throughput.py",
        "scripts/status_bar_throughput_classic_cli_smoke.py",
        "audits/StatusBarThroughputE2E.harness.py",
        "audits/StatusBarThroughputE2E.core.ps1",
        "audits/RUN_STATUS_BAR_THROUGHPUT_E2E.bat",
        "overlay/hermes_cli/status_bar_prompt_elapsed.py",
        "scripts/verify_fork_status_bar_display.py",
        "tests/hermes_cli/test_status_bar_prompt_elapsed.py",
    ]
    ok = all((REPO_ROOT / p).is_file() for p in required)
    _step("repo-artefacten aanwezig", ok)


def test_e2_overlay_hooks_and_placement() -> None:
    fork = _read("overlay/hermes_cli/cli_fork_patch.py")
    cmds = _read("overlay/hermes_cli/cli_command_patches.py")
    ok = (
        "_append_status_bar_throughput_fragments" in fork
        and "_freeze_stream_tps_segment" in fork
        and "_record_stream_tps_delta" in fork
        and "live_throughput_snapshot" in fork
        and "_resolve_tps_command" in cmds
        and "handle_tps_command" in cmds
        and fork.find("_append_status_bar_cost_fragments")
        < fork.find("_append_status_bar_throughput_fragments")
    )
    tier_a = _read("cli.py")
    ok = ok and "_handle_tps_command" not in tier_a and "_append_status_bar_cost_fragments" not in tier_a
    _step("overlay hooks + throughput na cost; Tier A cli schoon", ok)


def test_e3_tps_command_and_display_default() -> None:
    tps_cmd = _read("overlay/hermes_cli/cli_tps_command.py")
    fork = _read("overlay/hermes_cli/cli_fork_patch.py")
    ok = (
        "show_status_bar_tps" in tps_cmd
        and "display.show_status_bar_tps" in tps_cmd
        and "_show_status_bar_tps" in fork
        and 'get("show_status_bar_tps", True)' in fork
    )
    _step("/tps overlay command + display default via fork patch", ok)


def test_e4_tui_overlay_throughput() -> None:
    tui = _read("overlay/ui-tui/src/domain/statusBarThroughput.ts")
    ok = "statusBarThroughput" in tui or "formatStatusBarTps" in tui or "tok/s" in tui
    _step("TUI throughput module in overlay (geen Tier A gateway-RPC vereist)", ok)


def test_e5_agent_finalize_and_stream_delta() -> None:
    from overlay.bootstrap import install

    install()
    from hermes_cli.status_bar_throughput import (
        finalize_agent_call_tps,
        live_throughput_snapshot,
        record_agent_stream_delta,
        reset_agent_stream_tps_live,
    )

    agent = SimpleNamespace(
        _stream_gen_started_at=None,
        _stream_gen_tokens_est=0,
        _last_call_tps=None,
    )
    record_agent_stream_delta(agent, "hello world " * 20)
    ok_track = agent._stream_gen_started_at is not None and agent._stream_gen_tokens_est > 0
    time.sleep(0.6)
    finalize_agent_call_tps(agent, completion_tokens=120, api_duration=10.0)
    ok_fin = agent._last_call_tps is not None and agent._last_call_tps >= 10
    snap = live_throughput_snapshot(agent)
    ok_snap = snap["last_call_tps"] == agent._last_call_tps
    reset_agent_stream_tps_live(agent)
    ok_reset = agent._stream_gen_started_at is None and agent._stream_gen_tokens_est == 0
    _step("agent stream tracking + finalize + snapshot", ok_track and ok_fin and ok_snap and ok_reset)


def test_e6_freeze_guard_cli() -> None:
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli._stream_tps_started_at = time.time() - 1.0
    cli._stream_tps_tokens_est = 100
    cli._last_call_tps = None
    cli.agent = SimpleNamespace(_last_call_tps=88.0)
    cli._freeze_stream_tps_segment()
    ok = cli.agent._last_call_tps == 88.0 and cli._stream_tps_started_at is None
    _step("CLI freeze overschrijft agent _last_call_tps niet", ok)


def test_e7_formatter_edge_cases() -> None:
    from overlay.bootstrap import install

    install()
    from hermes_cli.status_bar_throughput import (
        compute_live_tps,
        format_status_bar_tps,
        live_throughput_snapshot,
        resolve_status_bar_throughput_label,
    )

    ok = (
        format_status_bar_tps(float("nan")) is None
        and compute_live_tps(100, 1000.0, now=1000.2) is None
        and compute_live_tps(100, 1000.0, now=1002.0) == 50.0
        and resolve_status_bar_throughput_label(
            {"stream_tps": 80.0, "last_call_tps": 10.0},
            show_tps=True,
            width=120,
        )
        == "80 tok/s"
        and resolve_status_bar_throughput_label(
            {"last_call_tps": 40.0},
            show_tps=True,
            width=60,
        )
        is None
        and live_throughput_snapshot(
            SimpleNamespace(
                _stream_gen_started_at=1000.0,
                _stream_gen_tokens_est=100,
                _last_call_tps=77.0,
            ),
            cli_started_at=500.0,
            cli_tokens_est=999,
            cli_last_call_tps=1.0,
            now=1002.0,
        )["last_call_tps"]
        == 77.0
    )
    _step("formatter: NaN, min elapsed, width gate, agent priority", ok)


def _run_pytest(paths: list[str], extra: list[str] | None = None) -> tuple[bool, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    args = [
        sys.executable,
        "-m",
        "pytest",
        *[str(REPO_ROOT / p) for p in paths],
        "-q",
        "-o",
        "addopts=",
        *(extra or []),
    ]
    try:
        proc = subprocess.run(
            args,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            check=False,
            env=env,
        )
    except Exception as exc:
        return False, str(exc)
    tail = (proc.stdout or proc.stderr or "")[-500:]
    return proc.returncode == 0, tail.strip()


def test_e8_pytest_throughput_module() -> None:
    ok, tail = _run_pytest(["tests/hermes_cli/test_status_bar_throughput.py"])
    _step("pytest test_status_bar_throughput.py", ok, tail)


def test_e9_pytest_cli_status_bar_throughput() -> None:
    ok, tail = _run_pytest(
        ["tests/cli/test_cli_status_bar.py"],
        ["-k", "throughput or tok"],
    )
    _step("pytest cli status bar throughput", ok, tail)


def test_e10_classic_cli_smoke() -> None:
    smoke = REPO_ROOT / "scripts/status_bar_throughput_classic_cli_smoke.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    try:
        proc = subprocess.run(
            [sys.executable, str(smoke)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
            env=env,
        )
    except Exception as exc:
        _step("classic CLI throughput smoke", False, str(exc))
        return
    tail = (proc.stdout or proc.stderr or "")[-400:]
    ok = proc.returncode == 0
    _step("classic CLI throughput smoke", ok, tail.strip() if not ok else "")


def test_e11_tui_npm_tests() -> None:
    ui_tui = REPO_ROOT / "ui-tui"
    if not (ui_tui / "package.json").is_file():
        _step("ui-tui npm throughput tests (skip)", True, "ui-tui ontbreekt")
        return
    import shutil

    if not shutil.which("npm"):
        _step("ui-tui npm throughput tests (skip)", True, "npm ontbreekt")
        return
        return
    overlay_test = REPO_ROOT / "overlay/ui-tui/src/__tests__/statusBarThroughput.test.ts"
    if not overlay_test.is_file():
        _step("ui-tui npm throughput tests (skip)", True, "overlay vitest ontbreekt")
        return
    if not (ui_tui / "node_modules").is_dir():
        _step(
            "ui-tui npm throughput tests (skip)",
            True,
            "node_modules ontbreekt — draai build_fork_ui_assets lokaal",
        )
        return
    try:
        proc = subprocess.run(
            ["npx", "vitest", "run", "src/__tests__/statusBarThroughput.test.ts", "--passWithNoTests"],
            cwd=str(ui_tui),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            check=False,
        )
    except Exception as exc:
        _step("ui-tui npm throughput tests (skip)", True, str(exc))
        return
    ok = proc.returncode == 0
    detail = "" if ok else (proc.stdout or proc.stderr or "")[-300:]
    _step("ui-tui npm throughput + layout tests", ok, detail)


def test_e12_prompt_timer_module_and_config() -> None:
    mod = _read("overlay/hermes_cli/status_bar_prompt_elapsed.py")
    team = _read("windows/team_display.defaults")
    fork = _read("overlay/hermes_cli/cli_fork_patch.py")
    ok = (
        "format_prompt_elapsed_status_bar" in mod
        and "show_prompt_timer_emoji=false" in team.replace(" ", "")
        and "_format_prompt_elapsed" in fork
        and "status_bar_prompt_elapsed" in fork
    )
    _step("prompt timer overlay module + config default + fork patch", ok)


def test_e13_verify_fork_status_bar_display() -> None:
    script = REPO_ROOT / "scripts/verify_fork_status_bar_display.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
            env=env,
        )
    except Exception as exc:
        _step("verify_fork_status_bar_display.py", False, str(exc))
        return
    combined = f"{proc.stdout or ''}{proc.stderr or ''}"
    tail = combined[-300:]
    ok = proc.returncode == 0 and "PASS" in combined
    _step("verify_fork_status_bar_display.py", ok, tail.strip() if not ok else "")


def test_e14_pytest_prompt_timer() -> None:
    ok, tail = _run_pytest(["tests/hermes_cli/test_status_bar_prompt_elapsed.py"])
    _step("pytest test_status_bar_prompt_elapsed.py", ok, tail)


def main() -> int:
    print("=== Status Bar Throughput E2E ===")
    test_e1_repo_artefacts()
    test_e2_overlay_hooks_and_placement()
    test_e3_tps_command_and_display_default()
    test_e4_tui_overlay_throughput()
    test_e5_agent_finalize_and_stream_delta()
    test_e6_freeze_guard_cli()
    test_e7_formatter_edge_cases()
    test_e8_pytest_throughput_module()
    test_e9_pytest_cli_status_bar_throughput()
    test_e10_classic_cli_smoke()
    test_e11_tui_npm_tests()
    test_e12_prompt_timer_module_and_config()
    test_e13_verify_fork_status_bar_display()
    test_e14_pytest_prompt_timer()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
