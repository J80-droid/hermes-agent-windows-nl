#!/usr/bin/env python3
"""E2E: Nous overlay afwerking (2026-06) — dedup regel-§, trust preflight, bootstrap wiring.

Geen live API; valideert repo-artefacten + geïsoleerde subprocess/pytest.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FAILURES = 0
STEP = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" — {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def test_e1_deduplicate_line_section_split() -> None:
    path = REPO_ROOT / "scripts" / "deduplicate_memories.py"
    text = path.read_text(encoding="utf-8")
    ok = "SECTION_SPLIT_RE" in text and r"(?m)^\s*§\s*$" in text
    _step("deduplicate_memories regel-sectie split", ok)


def test_e2_deduplicate_pytest_subset() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(REPO_ROOT / "tests/scripts/test_deduplicate_memories.py"),
            str(REPO_ROOT / "tests/windows/test_legal_memory_language_layers.py"),
            "-q",
            "--tb=short",
            "-o",
            "addopts=",
            "-k",
            "deduplicate",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "passed" in combined.lower()
    _step("pytest dedup subset", ok, f"exit={proc.returncode}")


def test_e3_run_audits_trust_and_fork_gates() -> None:
    text = (REPO_ROOT / "windows/audits/RUN_AUDITS.ps1").read_text(encoding="utf-8")
    ok = (
        "function Invoke-TrustMemorySyncPreflight" in text
        and "trust-runtime-preflight" in text
        and "nous-overlay-fork-gates-e2e" in text
        and "Get-NativeExitCode" in text
    )
    _step("RUN_AUDITS trust preflight + fork gates", ok)


def test_e4_sync_trust_runtime_retry() -> None:
    text = (REPO_ROOT / "windows/SYNC_TRUST_RUNTIME.bat").read_text(encoding="utf-8")
    ok = "eenmalige SOUL+memory retry" in text and "sync_soul_anatomy_snippets.ps1" in text
    _step("SYNC_TRUST_RUNTIME legal retry keten", ok)


def test_e5_collect_env_sync_keys_bootstrap() -> None:
    script = REPO_ROOT / "windows/scripts/collect_env_sync_keys.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
        env=env,
    )
    ok = proc.returncode == 0
    detail = "" if ok else f"exit={proc.returncode}"
    _step("collect_env_sync_keys.py exit 0", ok, detail)


def test_e6_bootstrap_overlay_modules() -> None:
    from overlay import bootstrap

    ok = all(
        stem in bootstrap._OVERLAY_HERMES_CLI_MODULES  # type: ignore[attr-defined]
        for stem in ("filesystem_sandbox", "hardware_backend", "config_snapshot", "profile_mcp_format")
    )
    _step("bootstrap overlay modules (sandbox/hw/snapshot)", ok)


def test_e7_overlay_usage_ts() -> None:
    path = REPO_ROOT / "overlay/ui-tui/src/domain/usage.ts"
    ok = path.is_file()
    if ok:
        text = path.read_text(encoding="utf-8")
        ok = "formatStatusBarCost" in text and "mergeUsage" in text
    _step("overlay ui-tui usage.ts cost helpers", ok)


def test_e8_enforce_legal_seed_guard() -> None:
    text = (REPO_ROOT / "windows/scripts/enforce_profile_memory_char_limits.ps1").read_text(
        encoding="utf-8"
    )
    ok = "legal USER.md" in text and "Test-MemoryLegalDomainSection" in text
    _step("enforce_profile_memory legal seed guard", ok)


def main() -> int:
    print("=== Nous Overlay Afwerking E2E ===", flush=True)
    test_e1_deduplicate_line_section_split()
    test_e2_deduplicate_pytest_subset()
    test_e3_run_audits_trust_and_fork_gates()
    test_e4_sync_trust_runtime_retry()
    test_e5_collect_env_sync_keys_bootstrap()
    test_e6_bootstrap_overlay_modules()
    test_e7_overlay_usage_ts()
    test_e8_enforce_legal_seed_guard()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr, flush=True)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
