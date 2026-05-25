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
        "hermes_cli/status_bar_throughput.py",
        "ui-tui/src/domain/statusBarThroughput.ts",
        "cli.py",
        "hermes_cli/config.py",
        "hermes_cli/commands.py",
        "hermes_cli/usage_snapshot.py",
        "run_agent.py",
        "agent/conversation_loop.py",
        "agent/agent_init.py",
        "tui_gateway/server.py",
        "tests/hermes_cli/test_status_bar_throughput.py",
        "scripts/status_bar_throughput_classic_cli_smoke.py",
        "audits/StatusBarThroughputE2E.harness.py",
        "audits/StatusBarThroughputE2E.core.ps1",
        "audits/RUN_STATUS_BAR_THROUGHPUT_E2E.bat",
    ]
    ok = all((REPO_ROOT / p).is_file() for p in required)
    _step("repo-artefacten aanwezig", ok)


def test_e2_cli_hooks_and_placement() -> None:
    cli = _read("cli.py")
    ok = (
        "_append_status_bar_throughput_fragments" in cli
        and "_handle_tps_command" in cli
        and 'canonical == "tps"' in cli
        and "_show_status_bar_tps" in cli
        and "live_throughput_snapshot" in cli
        and "_freeze_stream_tps_segment" in cli
        and cli.find("_append_status_bar_cost_fragments")
        < cli.find("_append_status_bar_throughput_fragments")
    )
    _step("cli.py hooks + throughput na cost-segment", ok)


def test_e3_commands_and_config() -> None:
    commands = _read("hermes_cli/commands.py")
    config = _read("hermes_cli/config.py")
    ok = (
        '"tps"' in commands
        and "show_status_bar_tps" in config
    )
    _step("/tps command + display.show_status_bar_tps default", ok)


def test_e4_gateway_config_rpc() -> None:
    gw = _read("tui_gateway/server.py")
    ok = "show_status_bar_tps" in gw and "status_bar_tps" in gw
    _step("tui_gateway config.get/set voor throughput", ok)


def test_e5_agent_finalize_and_stream_delta() -> None:
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
        _step("ui-tui npm throughput tests", False, "ui-tui ontbreekt")
        return
    try:
        proc = subprocess.run(
            [
                "npm",
                "test",
                "--",
                "--run",
                "src/__tests__/statusBarThroughput.test.ts",
                "src/__tests__/usageCostBar.test.ts",
            ],
            cwd=str(ui_tui),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            check=False,
            shell=True,
        )
    except Exception as exc:
        _step("ui-tui npm throughput tests", False, str(exc))
        return
    tail = (proc.stdout or proc.stderr or "")[-500:]
    ok = proc.returncode == 0
    _step("ui-tui npm throughput + layout tests", ok, tail.strip() if not ok else "")


def main() -> int:
    print("=== Status Bar Throughput E2E ===")
    test_e1_repo_artefacts()
    test_e2_cli_hooks_and_placement()
    test_e3_commands_and_config()
    test_e4_gateway_config_rpc()
    test_e5_agent_finalize_and_stream_delta()
    test_e6_freeze_guard_cli()
    test_e7_formatter_edge_cases()
    test_e8_pytest_throughput_module()
    test_e9_pytest_cli_status_bar_throughput()
    test_e10_classic_cli_smoke()
    test_e11_tui_npm_tests()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
