#!/usr/bin/env python3
"""E2E: fork tests/hermes_cli/ migratie + hygiene guard (geen live netwerk).

Valideert dat de 35 fork-only tests naar tests/overlay/ of tests/windows/ zijn
verplaatst, dat tests/hermes_cli/ upstream-pariteit heeft, en dat de staged-guard
nieuwe toevoegingen blokkeert.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

CHECK_SCRIPT = REPO / "windows/scripts/check_fork_hermes_cli_tests.py"
EXCEPTIONS = REPO / "windows/tests/fork_hermes_cli_test_exceptions.txt"
GATE_MANIFEST = REPO / "windows/tests/pytest_fork_gate.yaml"
PS_WRAPPER = REPO / "windows/scripts/Test-ForkHermesCliTestHygiene.ps1"

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

MIGRATED_OVERLAY_SAMPLES = (
    "tests/overlay/test_profile_switch.py",
    "tests/overlay/test_normalizer_ts_parity.py",
    "tests/overlay/test_status_bar_cost.py",
)
MIGRATED_WINDOWS_SAMPLE = "tests/windows/test_win32_console.py"


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


def _run_check(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [str(PY), str(CHECK_SCRIPT), *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )


def _active_exception_paths() -> list[str]:
    lines: list[str] = []
    for line in EXCEPTIONS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def test_e1_repo_artefacts_present() -> None:
    required = [
        CHECK_SCRIPT,
        EXCEPTIONS,
        GATE_MANIFEST,
        PS_WRAPPER,
        REPO / MIGRATED_OVERLAY_SAMPLES[0],
        REPO / MIGRATED_WINDOWS_SAMPLE,
        REPO / "docs/FORK_TEST_MIGRATION_BACKLOG.md",
    ]
    missing = [str(p.relative_to(REPO)) for p in required if not p.is_file()]
    _step("repo-artefacten migratie + guard", not missing, ", ".join(missing) or "OK")


def test_e2_exceptions_list_empty() -> None:
    active = _active_exception_paths()
    _step("fork_hermes_cli_test_exceptions.txt leeg", not active, f"{len(active)} pad(en)")


def test_e3_hermes_cli_upstream_parity() -> None:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "upstream/main", "--", "tests/hermes_cli/"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    ok = proc.returncode == 0 and not (proc.stdout or "").strip()
    detail = (proc.stdout or proc.stderr or "").strip()[:120]
    _step("tests/hermes_cli/ geen diff vs upstream/main", ok, detail or "clean")


def test_e4_pre_merge_strict_passes() -> None:
    proc = _run_check("--pre-merge", "--upstream", "upstream/main", "--strict", "--repo", str(REPO))
    ok = proc.returncode == 0
    detail = (proc.stderr or proc.stdout or f"exit={proc.returncode}")[-160:]
    _step("check_fork_hermes_cli_tests --pre-merge --strict", ok, detail)


def test_e5_pre_merge_json_upstream_parity_clean() -> None:
    proc = _run_check("--pre-merge", "--json", "--repo", str(REPO))
    ok = proc.returncode == 0
    detail = "invalid json"
    if ok:
        try:
            payload = json.loads(proc.stdout)
            ok = (
                payload.get("mode") == "pre-merge"
                and payload.get("upstream_parity_clean") is True
                and int(payload.get("conflict_risk_total", -1)) == 0
            )
            detail = f"parity={payload.get('upstream_parity_clean')}"
        except json.JSONDecodeError:
            ok = False
    _step("pre-merge JSON upstream_parity_clean", ok, detail)


def test_e6_gate_manifest_no_hermes_cli_paths() -> None:
    text = _read("windows/tests/pytest_fork_gate.yaml")
    bad = "tests/hermes_cli/" in text
    ok = GATE_MANIFEST.is_file() and "tests/overlay/" in text and not bad
    _step("pytest_fork_gate.yaml overlay-only (geen hermes_cli paden)", ok)


def test_e7_migrated_samples_not_under_hermes_cli() -> None:
    stale = [
        p
        for p in (*MIGRATED_OVERLAY_SAMPLES, MIGRATED_WINDOWS_SAMPLE)
        if (REPO / "tests/hermes_cli" / Path(p).name).is_file()
    ]
    _step("gemigreerde samples niet meer in tests/hermes_cli/", not stale, ", ".join(stale) or "OK")


def test_e8_staged_guard_blocks_new_hermes_cli_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        mini = Path(tmp) / "mini"
        (mini / "windows" / "tests").mkdir(parents=True)
        (mini / "windows" / "scripts").mkdir(parents=True)
        (mini / "tests" / "hermes_cli").mkdir(parents=True)

        (mini / "windows" / "scripts" / "check_fork_hermes_cli_tests.py").write_text(
            CHECK_SCRIPT.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (mini / "windows" / "tests" / "fork_hermes_cli_test_exceptions.txt").write_text(
            textwrap.dedent(
                """
                # mini repo — no exceptions
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        offender = mini / "tests" / "hermes_cli" / "test_new_fork_only.py"
        offender.write_text("def test_x(): pass\n", encoding="utf-8")

        init = subprocess.run(["git", "init", "-q"], cwd=str(mini), capture_output=True, text=True)
        if init.returncode != 0:
            _step("staged guard mini-repo git init", False, init.stderr or init.stdout)
            return
        subprocess.run(["git", "add", "."], cwd=str(mini), capture_output=True, text=True, check=False)

        proc = _run_check("--staged", "--repo", str(mini))
        ok = proc.returncode != 0 and "test_new_fork_only.py" in (proc.stderr or "")
        _step("staged guard blokkeert nieuwe tests/hermes_cli/", ok, f"exit={proc.returncode}")


def test_e9_ps_wrapper_invokes_python_checker() -> None:
    text = PS_WRAPPER.read_text(encoding="utf-8", errors="replace")
    ok = "check_fork_hermes_cli_tests.py" in text and "--pre-merge" in text
    _step("Test-ForkHermesCliTestHygiene.ps1 wrapper", ok)


def main() -> int:
    test_e1_repo_artefacts_present()
    test_e2_exceptions_list_empty()
    test_e3_hermes_cli_upstream_parity()
    test_e4_pre_merge_strict_passes()
    test_e5_pre_merge_json_upstream_parity_clean()
    test_e6_gate_manifest_no_hermes_cli_paths()
    test_e7_migrated_samples_not_under_hermes_cli()
    test_e8_staged_guard_blocks_new_hermes_cli_file()
    test_e9_ps_wrapper_invokes_python_checker()

    print(f"\n=== Fork hermes_cli test migration E2E: {STEP - FAILURES}/{STEP} passed ===")
    if FAILURES:
        print(f"=== FAIL ({FAILURES} step(s)) ===", file=sys.stderr)
        return 1
    print("=== ALL PASS ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
