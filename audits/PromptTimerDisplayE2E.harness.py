#!/usr/bin/env python3
"""E2E: status bar prompt timer without emoji (fork-owned, upstream-safe).

No live API, no PTY. Covers module formatting, config defaults, cli delegation,
verify script, classic CLI snapshot, slash command, merge keepOurs, and pytest gates.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0
STEP = 0
_TIMER_CHARS = ("\u23f1", "\u23f2")


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
        "hermes_cli/status_bar_prompt_elapsed.py",
        "scripts/verify_fork_status_bar_display.py",
        "tests/hermes_cli/test_status_bar_prompt_elapsed.py",
        "tests/cli/test_cli_status_bar.py",
        "hermes_cli/config.py",
        "hermes_cli/commands.py",
        "cli.py",
        "windows/team_display.defaults",
        "cli-config.yaml.example",
        "windows/merge_upstream_fork.ps1",
        "audits/PromptTimerDisplayE2E.harness.py",
        "audits/PromptTimerDisplayE2E.core.ps1",
        "audits/RUN_PROMPT_TIMER_DISPLAY_E2E.bat",
    ]
    ok = all((REPO_ROOT / p).is_file() for p in required)
    _step("repo-artefacten aanwezig", ok)


def test_e2_module_no_emoji_and_finite_guards() -> None:
    from hermes_cli.status_bar_prompt_elapsed import (
        format_prompt_elapsed_status_bar,
        prompt_elapsed_contains_emoji,
    )

    out_default = format_prompt_elapsed_status_bar(None, 26.0, show_emoji=False)
    out_nan = format_prompt_elapsed_status_bar(None, float("nan"), show_emoji=False)
    future = time.time() + 7200.0
    out_future = format_prompt_elapsed_status_bar(
        future, 0.0, live=True, show_emoji=False, now=time.time()
    )
    out_emoji = format_prompt_elapsed_status_bar(None, 12.0, show_emoji=True, live=False)
    ok = (
        out_default == "26s"
        and not prompt_elapsed_contains_emoji(out_default)
        and out_nan == "0s"
        and out_future == "0s"
        and out_emoji.startswith("\u23f2 ")
        and prompt_elapsed_contains_emoji(out_emoji)
    )
    _step("module: geen emoji default + finite guards + emoji parity", ok)


def test_e3_config_and_team_defaults() -> None:
    cfg = _read("hermes_cli/config.py")
    team = _read("windows/team_display.defaults")
    example = _read("cli-config.yaml.example")
    ok = (
        ("show_prompt_timer_emoji\": False" in cfg or "show_prompt_timer_emoji': False" in cfg)
        and "show_prompt_timer_emoji=false" in team.replace(" ", "")
        and "show_prompt_timer_emoji" in example
    )
    _step("config + team_display + example documentatie", ok)


def test_e4_cli_delegation_and_truthy_init() -> None:
    cli = _read("cli.py")
    ok = (
        "status_bar_prompt_elapsed" in cli
        and "format_prompt_elapsed_status_bar" in cli
        and "_show_prompt_timer_emoji" in cli
        and "is_truthy_value" in cli
        and "_handle_timer_emoji_command" in cli
        and 'canonical == "timer-emoji"' in cli
        and 'return f"{emoji}' not in cli.split("def _format_prompt_elapsed")[1].split("\n    def ")[0]
    )
    _step("cli.py delegatie + is_truthy_value + /timer-emoji hook", ok)


def test_e5_verify_fork_script() -> None:
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
    tail = (proc.stdout or proc.stderr or "")[-400:]
    ok = proc.returncode == 0 and "PASS" in (proc.stdout or "")
    _step("verify_fork_status_bar_display.py", ok, tail.strip() if not ok else "")


def test_e6_classic_cli_snapshot_and_status_bar() -> None:
    from cli import HermesCLI

    cli = HermesCLI.__new__(HermesCLI)
    cli.model = "anthropic/claude-sonnet-4-20250514"
    cli.session_start = datetime.now() - timedelta(minutes=1)
    cli.conversation_history = [{"role": "user", "content": "hi"}]
    cli.agent = None
    cli._show_cost = True
    cli._show_status_bar_tps = False
    cli._show_prompt_timer_emoji = False
    cli._cost_bar_mode = "rich"
    cli._last_call_tps = None
    cli._stream_tps_started_at = None
    cli._stream_tps_tokens_est = 0
    cli._prompt_start_time = None
    cli._prompt_duration = 26.0

    elapsed = cli._format_prompt_elapsed(None, 26.0, live=False)
    snap = cli._get_status_bar_snapshot()
    snap_elapsed = snap.get("prompt_elapsed") or ""
    bar = cli._build_status_bar_text(width=120)

    ok = (
        elapsed == "26s"
        and not any(ch in elapsed for ch in _TIMER_CHARS)
        and snap_elapsed == elapsed
        and "26s" in bar
        and not any(ch in bar for ch in _TIMER_CHARS)
    )
    _step("classic CLI: snapshot + statusbalk zonder timer-emoji", ok)


def test_e7_timer_emoji_toggle_path() -> None:
    commands = _read("hermes_cli/commands.py")
    cli = _read("cli.py")
    ok = (
        '"timer-emoji"' in commands
        and 'save_config_value("display.show_prompt_timer_emoji"' in cli
    )
    _step("/timer-emoji command + config persist", ok)


def test_e8_merge_upstream_keep_ours() -> None:
    ps1 = _read("windows/merge_upstream_fork.ps1")
    ok = "status_bar_prompt_elapsed.py" in ps1 and "test_status_bar_prompt_elapsed.py" in ps1
    _step("merge_upstream_fork.ps1 keepOurs prompt-timer bestanden", ok)


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


def _run_inline_module_tests() -> tuple[bool, str]:
    spec = importlib.util.spec_from_file_location(
        "test_status_bar_prompt_elapsed",
        REPO_ROOT / "tests/hermes_cli/test_status_bar_prompt_elapsed.py",
    )
    if spec is None or spec.loader is None:
        return False, "could not load test module"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    failures: list[str] = []
    for name in sorted(dir(mod)):
        if not name.startswith("test_"):
            continue
        fn = getattr(mod, name)
        try:
            fn()
        except Exception as exc:
            failures.append(f"{name}: {exc}")
    if failures:
        return False, "; ".join(failures[:5])
    return True, f"inline {len([n for n in dir(mod) if n.startswith('test_')])} tests"


def test_e9_pytest_prompt_elapsed_module() -> None:
    ok, tail = _run_pytest(["tests/hermes_cli/test_status_bar_prompt_elapsed.py"])
    if not ok and ("No module named pytest" in tail or "No module named 'pytest'" in tail):
        ok, tail = _run_inline_module_tests()
        _step("unit tests test_status_bar_prompt_elapsed (inline fallback)", ok, tail)
        return
    _step("pytest test_status_bar_prompt_elapsed.py", ok, tail)


def _run_inline_cli_prompt_tests() -> tuple[bool, str]:
    from tests.cli.test_cli_status_bar import TestCLIStatusBar

    inst = TestCLIStatusBar()
    cases = (
        inst.test_prompt_elapsed_snapshot_has_no_emoji_by_default,
        inst.test_prompt_elapsed_with_emoji_when_enabled,
    )
    failures: list[str] = []
    for fn in cases:
        try:
            fn()
        except Exception as exc:
            failures.append(f"{fn.__name__}: {exc}")
    if failures:
        return False, "; ".join(failures)
    return True, f"inline {len(cases)} cli prompt_elapsed tests"


def test_e10_pytest_cli_prompt_elapsed() -> None:
    ok, tail = _run_pytest(
        ["tests/cli/test_cli_status_bar.py"],
        extra=["-k", "prompt_elapsed"],
    )
    if not ok and ("No module named pytest" in tail or "No module named 'pytest'" in tail):
        ok, tail = _run_inline_cli_prompt_tests()
        _step("cli prompt_elapsed tests (inline fallback)", ok, tail)
        return
    _step("pytest cli -k prompt_elapsed", ok, tail)


def main() -> int:
    print("=== Prompt Timer Display E2E ===")
    test_e1_repo_artefacts()
    test_e2_module_no_emoji_and_finite_guards()
    test_e3_config_and_team_defaults()
    test_e4_cli_delegation_and_truthy_init()
    test_e5_verify_fork_script()
    test_e6_classic_cli_snapshot_and_status_bar()
    test_e7_timer_emoji_toggle_path()
    test_e8_merge_upstream_keep_ours()
    test_e9_pytest_prompt_elapsed_module()
    test_e10_pytest_cli_prompt_elapsed()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
