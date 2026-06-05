#!/usr/bin/env python3
"""E2E: Nous overlay runtime wiring (P0–P5) — no live API.

Covers bootstrap patches, agent throughput fork, CLI stream wrap resilience,
/tps + /cost dispatch, freeze guard, tier-A guard script, and overlay pytest.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


def test_e1_runtime_artefacts() -> None:
    required = [
        "overlay/bootstrap.py",
        "overlay/agent/agent_throughput_fork_patch.py",
        "overlay/hermes_cli/cli_fork_patch.py",
        "overlay/hermes_cli/cli_command_patches.py",
        "overlay/hermes_cli/cli_tps_command.py",
        "overlay/hermes_cli/cli_tps_stream_hooks.py",
        "overlay/hermes_cli/cli_cost_command.py",
        "overlay/scripts/verify_institutional_guard.py",
        "tests/overlay/test_agent_throughput_fork_patch.py",
    ]
    ok = all((REPO_ROOT / p).is_file() for p in required)
    _step("runtime patch artefacten", ok)


def test_e2_bootstrap_patches_idempotent() -> None:
    from overlay.bootstrap import install

    install()
    install()

    from cli import HermesCLI
    from run_agent import AIAgent
    import agent.context_compressor as cc
    import agent.usage_pricing as up
    import hermes_cli.models as models_mod

    ok = (
        getattr(HermesCLI, "_fork_status_bar_patch_applied", False)
        and getattr(HermesCLI, "_fork_stream_delta_wrapped", False)
        and hasattr(HermesCLI, "_record_stream_tps_delta")
        and hasattr(HermesCLI, "_handle_tps_command")
        and getattr(AIAgent, "_fork_throughput_patch_applied", False)
        and getattr(cc.ContextCompressor, "_fork_throughput_update_wrapped", False)
        and getattr(up, "_fork_google_pricing_patch_applied", False)
        and getattr(models_mod, "_fork_catalog_patch_applied", False)
    )
    _step("bootstrap patches idempotent (CLI + agent + pricing + models)", ok)


def test_e3_agent_compressor_backlink() -> None:
    from overlay.agent.agent_throughput_fork_patch import _link_compressor_to_agent

    agent = SimpleNamespace(context_compressor=SimpleNamespace())
    _link_compressor_to_agent(agent)
    ok = getattr(agent.context_compressor, "_fork_throughput_agent", None) is agent
    _step("compressor._fork_throughput_agent back-link", ok)


def test_e4_agent_fire_stream_delta_records_tokens() -> None:
    from overlay.bootstrap import install

    install()
    from run_agent import AIAgent

    agent = AIAgent.__new__(AIAgent)
    agent._stream_gen_started_at = None
    agent._stream_gen_tokens_est = 0
    agent.stream_delta_callback = None
    agent._stream_callback = None
    agent._stream_needs_break = False
    agent._stream_think_scrubber = None

    AIAgent._fire_stream_delta(agent, "hello throughput smoke " * 5)
    ok = agent._stream_gen_tokens_est > 0 and agent._stream_gen_started_at is not None
    _step("AIAgent._fire_stream_delta records estimated tokens", ok)


def test_e5_compressor_update_finalizes_agent_tps() -> None:
    from overlay.bootstrap import install

    install()
    from agent.context_compressor import ContextCompressor

    compressor = ContextCompressor.__new__(ContextCompressor)
    compressor.last_prompt_tokens = 0
    compressor.last_completion_tokens = 0
    compressor.last_total_tokens = 0
    compressor.threshold_tokens = 100_000
    compressor.awaiting_real_usage_after_compression = False
    compressor.last_compression_rough_tokens = 0
    compressor.last_real_prompt_tokens = 0
    compressor.last_rough_tokens_when_real_prompt_fit = 0

    agent = SimpleNamespace(
        _stream_gen_started_at=time.time() - 1.5,
        _stream_gen_tokens_est=80,
        _last_call_tps=None,
    )
    setattr(compressor, "_fork_throughput_agent", agent)

    compressor.update_from_response({"completion_tokens": 120, "prompt_tokens": 500})
    ok = getattr(agent, "_last_call_tps", None) is not None and agent._last_call_tps > 0
    _step("ContextCompressor.update_from_response finalizes agent tok/s", ok)


def test_e6_stream_delta_none_boundary_freezes() -> None:
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli._flush_stream = MagicMock()
    cli._reset_stream_state = MagicMock()
    cli._stream_tps_started_at = time.time() - 1.0
    cli._stream_tps_tokens_est = 60
    cli._last_call_tps = None
    cli.agent = None

    ok = getattr(HermesCLI, "_fork_stream_delta_wrapped", False)
    HermesCLI._stream_delta(cli, None)
    ok = ok and cli._flush_stream.called and cli._reset_stream_state.called
    ok = ok and cli._stream_tps_tokens_est == 0
    _step("CLI _stream_delta(None) freeze + flush turn boundary", ok)


def test_e7_slash_commands_tps_and_cost() -> None:
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.config = MagicMock()
    cli.config.get.return_value = {}
    cli._show_status_bar_tps = True
    cli._show_cost = True
    cli._cost_bar_mode = "rich"
    cli._invalidate = MagicMock()

    with patch("cli._cprint"), patch("cli.save_config_value", return_value=True):
        tps_ok = HermesCLI.process_command(cli, "/tps off") is True
        cost_ok = HermesCLI.process_command(cli, "/cost status") is True
        state_ok = cli._show_status_bar_tps is False
    ok = tps_ok and cost_ok and state_ok
    _step("/tps off + /cost status via process_command", ok)


def test_e8_freeze_guard_agent_tps() -> None:
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli._stream_tps_started_at = time.time() - 1.0
    cli._stream_tps_tokens_est = 100
    cli._last_call_tps = None
    cli.agent = SimpleNamespace(_last_call_tps=88.0)

    HermesCLI._freeze_stream_tps_segment(cli)
    ok = cli.agent._last_call_tps == 88.0 and cli._last_call_tps is None
    _step("CLI freeze overschrijft agent._last_call_tps niet", ok)


def test_e9_tier_a_guard_script() -> None:
    script = REPO_ROOT / "scripts" / "verify_institutional_guard.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, str(script), "--check-tier-a-cli"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
        env=env,
    )
    tail = (proc.stdout or proc.stderr or "")[-300:]
    ok = proc.returncode == 0 and "geen fork-only" in (proc.stdout or "").lower()
    _step("verify_institutional_guard --check-tier-a-cli", ok, tail.strip() if not ok else "")


def test_e10_pytest_overlay_runtime_subset() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/overlay/test_agent_throughput_fork_patch.py",
            "tests/overlay/test_cli_tps_stream_hooks.py",
            "tests/overlay/test_cli_tps_command.py",
            "tests/overlay/test_cli_command_patches.py",
            "-q",
            "-o",
            "addopts=",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
        env=env,
    )
    tail = (proc.stdout or proc.stderr or "")[-400:]
    ok = proc.returncode == 0
    _step("pytest overlay runtime subset", ok, tail.strip() if not ok else "")


def main() -> int:
    print("=== Nous Overlay Runtime E2E ===")
    test_e1_runtime_artefacts()
    test_e2_bootstrap_patches_idempotent()
    test_e3_agent_compressor_backlink()
    test_e4_agent_fire_stream_delta_records_tokens()
    test_e5_compressor_update_finalizes_agent_tps()
    test_e6_stream_delta_wrap_resilient()
    test_e7_slash_commands_tps_and_cost()
    test_e8_freeze_guard_agent_tps()
    test_e9_tier_a_guard_script()
    test_e10_pytest_overlay_runtime_subset()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
