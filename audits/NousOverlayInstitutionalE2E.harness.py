#!/usr/bin/env python3
"""Runtime harness for Nous overlay institutional E2E (no live API)."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _check_tier_a_cli_untouched() -> None:
    cli = (REPO / "cli.py").read_text(encoding="utf-8")
    if "_append_status_bar_cost_fragments" in cli:
        _fail("Tier A cli.py contains fork cost hook — must live in overlay patch only")
    if 'canonical == "cost"' in cli and "_handle_cost_command" in cli:
        _fail("Tier A cli.py contains inline /cost dispatch — use overlay/cli_command_patches")
    if 'canonical == "tps"' in cli and "_handle_tps_command" in cli:
        _fail("Tier A cli.py contains inline /tps dispatch — use overlay/cli_command_patches")
    if "_record_stream_tps_delta" in cli or "_freeze_stream_tps_segment" in cli:
        _fail("Tier A cli.py contains fork TPS stream hooks — use overlay/cli_fork_patch")
    _ok("Tier A cli.py has no inline fork cost/tps hooks")


def _check_overlay_artifacts() -> None:
    required = [
        "overlay/manifest.yaml",
        "overlay/bootstrap.py",
        "overlay/bootstrap_startup.py",
        "overlay/hermes_cli/cli_fork_patch.py",
        "overlay/hermes_cli/cli_command_patches.py",
        "overlay/hermes_cli/cli_cost_command.py",
        "overlay/hermes_cli/cli_tps_command.py",
        "overlay/hermes_cli/cli_tps_stream_hooks.py",
        "overlay/agent/agent_throughput_fork_patch.py",
        "overlay/hermes_cli/status_bar_cost.py",
        "overlay/hermes_cli/usage_snapshot.py",
        "overlay/hermes_cli/model_runtime_config.py",
        "overlay/hermes_cli/model_catalog_guard.py",
        "overlay/agent/google_gemini_pricing.py",
        "overlay/agent/pricing_fork_patch.py",
        "windows/scripts/Test-NousTreeIdentical.ps1",
        "windows/scripts/Invoke-ApplyHermesOverlay.ps1",
        "windows/scripts/sync_nous.ps1",
    ]
    for rel in required:
        if not (REPO / rel).is_file():
            _fail(f"missing overlay artefact: {rel}")
    _ok(f"overlay artefact tree ({len(required)} paths)")


def _check_bootstrap_runtime() -> None:
    from overlay.bootstrap import install

    install()
    install()  # idempotent

    import cli
    from cli import HermesCLI

    if not getattr(HermesCLI, "_fork_status_bar_patch_applied", False):
        _fail("HermesCLI missing _fork_status_bar_patch_applied")
    if not hasattr(HermesCLI, "_append_status_bar_cost_fragments"):
        _fail("HermesCLI missing _append_status_bar_cost_fragments after bootstrap")
    if not hasattr(HermesCLI, "_handle_cost_command"):
        _fail("HermesCLI missing _handle_cost_command after bootstrap")

    import hermes_cli.models as models_mod

    if not hasattr(models_mod, "model_default_passes_startup_catalog_guard"):
        _fail("hermes_cli.models missing catalog guard after bootstrap")

    import agent.usage_pricing as up

    if not getattr(up, "_fork_google_pricing_patch_applied", False):
        _fail("usage_pricing missing google pricing patch")

    _ok("bootstrap runtime patches (idempotent)")


def _check_status_bar_cost_runtime() -> None:
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.model = "anthropic/claude-sonnet-4-20250514"
    cli.session_start = datetime.now() - timedelta(minutes=5)
    cli.conversation_history = []
    cli._show_cost = True
    cli._cost_bar_mode = "rich"
    cli._show_status_bar_tps = True
    cli._status_bar_visible = True
    cli._status_bar_layout_lines = 1
    cli._model_picker_state = None
    cli.agent = SimpleNamespace(
        model=cli.model,
        provider="anthropic",
        base_url="",
        session_input_tokens=10_230,
        session_output_tokens=2_220,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_prompt_tokens=10_230,
        session_completion_tokens=2_220,
        session_total_tokens=12_450,
        session_api_calls=7,
        get_rate_limit_state=lambda: None,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=12_450,
            context_length=200_000,
            compression_count=0,
        ),
    )
    text = cli._build_status_bar_text(width=120)
    if "$" not in text:
        _fail(f"status bar missing cost label: {text!r}")
    _ok("status bar cost label at width=120")


def _check_gemini_pricing() -> None:
    from overlay.bootstrap import install

    install()
    from hermes_cli.usage_snapshot import build_session_usage_snapshot

    agent = SimpleNamespace(
        model="gemini-3.5-flash",
        provider="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        session_input_tokens=5000,
        session_output_tokens=500,
        session_cache_read_tokens=16000,
        session_cache_write_tokens=0,
        session_prompt_tokens=21000,
        session_completion_tokens=500,
        session_total_tokens=21500,
        session_api_calls=11,
        context_compressor=None,
    )
    usage = build_session_usage_snapshot(agent)
    if usage.get("cost_status") != "estimated":
        _fail(f"gemini cost_status expected estimated, got {usage.get('cost_status')!r}")
    if not usage.get("cost_usd"):
        _fail("gemini cost_usd missing")
    _ok("gemini pricing via overlay usage_snapshot")


def _check_cost_command_dispatch() -> None:
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli._show_cost = True
    cli._cost_bar_mode = "rich"
    cli._invalidate = lambda *a, **k: None
    ok = HermesCLI.process_command(cli, "/cost status")
    if ok is not True:
        _fail(f"/cost status expected True, got {ok!r}")
    _ok("/cost dispatch via process_command patch")


def _check_tps_command_and_stream_hooks() -> None:
    from overlay.bootstrap import install

    install()
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli._show_status_bar_tps = True
    cli._invalidate = lambda *a, **k: None
    cli._stream_tps_started_at = None
    cli._stream_tps_tokens_est = 0
    cli._last_call_tps = None
    cli.agent = None

    ok = HermesCLI.process_command(cli, "/tps status")
    if ok is not True:
        _fail(f"/tps status expected True, got {ok!r}")

    if not hasattr(HermesCLI, "_record_stream_tps_delta"):
        _fail("HermesCLI missing _record_stream_tps_delta after fork patch")
    if not hasattr(HermesCLI, "_freeze_stream_tps_segment"):
        _fail("HermesCLI missing _freeze_stream_tps_segment after fork patch")

    HermesCLI._record_stream_tps_delta(cli, "token estimate smoke text")
    if cli._stream_tps_tokens_est < 1:
        _fail("stream delta did not record estimated tokens")
    HermesCLI._freeze_stream_tps_segment(cli)
    if cli._stream_tps_tokens_est != 0:
        _fail("freeze did not reset stream token counter")

    _ok("/tps dispatch + stream hooks on HermesCLI")


def main() -> None:
    print("=== NousOverlayInstitutionalE2E harness ===")
    _check_overlay_artifacts()
    _check_tier_a_cli_untouched()
    _check_bootstrap_runtime()
    _check_status_bar_cost_runtime()
    _check_gemini_pricing()
    _check_cost_command_dispatch()
    _check_tps_command_and_stream_hooks()
    print("[OK] NousOverlayInstitutionalE2E harness PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
