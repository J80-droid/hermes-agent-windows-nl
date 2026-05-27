#!/usr/bin/env python3
"""E2E audit: Codebase Viz incremental SWR productiegate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN_API = REPO / "plugins/codebase-viz/dashboard/plugin_api.py"
README = REPO / "plugins/codebase-viz/dashboard/README.md"
OPS = REPO / "docs/INSTITUTIONAL_OPERATIONS.md"

FAILURES = 0
STEP = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] P{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] P{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def test_p1_scan_mode_parser_and_default_incremental() -> None:
    text = PLUGIN_API.read_text(encoding="utf-8")
    ok = (
        "_parse_scan_mode" in text
        and 'os.environ.get("CODEBASE_VIZ_SCAN_MODE", "incremental")' in text
        and "CODEBASE_VIZ_SCAN_MODE = _parse_scan_mode()" in text
    )
    _step("scan mode parser/default", ok)


def test_p2_snapshot_state_has_data_hashes() -> None:
    text = PLUGIN_API.read_text(encoding="utf-8")
    ok = (
        '"data_hashes": {}' in text
        and "_stable_data_hash" in text
        and "_mark_dataset_updated(key, result)" in text
    )
    _step("snapshot state + data hashes", ok)


def test_p3_swr_metadata_on_core_routes() -> None:
    text = PLUGIN_API.read_text(encoding="utf-8")
    required = [
        "served_from_cache",
        "refresh_in_background",
        "last_updated_at",
        "stale_age_sec",
        "scan_mode",
    ]
    ok = all(r in text for r in required) and "_with_swr_meta(cached" in text
    _step("SWR metadata in responses", ok)


def test_p4_signature_delta_fallback_refreshes_core_sets() -> None:
    text = PLUGIN_API.read_text(encoding="utf-8")
    ok = (
        'impacted.update({"pygount", "summary", "structure", "dependencies", "import_edges"})'
        in text
    )
    _step("signature-delta fallback", ok)


def test_p5_docs_describe_incremental_swr() -> None:
    readme = README.read_text(encoding="utf-8")
    ops = OPS.read_text(encoding="utf-8")
    ok = (
        "CODEBASE_VIZ_SCAN_MODE" in readme
        and "stale-while-revalidate" in readme
        and "CODEBASE_VIZ_SCAN_MODE" in ops
        and "delta-refresh" in ops
    )
    _step("docs updated for SWR", ok)


def test_p6_pytest_swr_subset() -> None:
    py = Path.home() / "miniconda3/envs/hermes-env/python.exe"
    if not py.is_file():
        py = Path(sys.executable)
    proc = subprocess.run(
        [
            str(py),
            "-m",
            "pytest",
            "tests/plugins/test_codebase_viz_plugin.py",
            "-q",
            "-o",
            "addopts=",
            "--tb=line",
            "-k",
            "scan_mode or swr or snapshot_data_hash or signature_delta",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
    )
    ok = proc.returncode == 0
    detail = ""
    if ok:
        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        detail = lines[-1] if lines else "pytest ok"
    else:
        detail = (proc.stdout + "\n" + proc.stderr).strip().splitlines()[-1][:180]
    _step("pytest SWR subset", ok, detail)


def main() -> int:
    print("=" * 60)
    print("  Codebase Viz incremental SWR E2E")
    print("=" * 60)

    tests = [name for name in globals() if name.startswith("test_p")]
    for name in sorted(tests):
        globals()[name]()

    print("\n" + "=" * 60)
    if FAILURES:
        print(f"  FAIL ({FAILURES}/{STEP})")
    else:
        print(f"  ALL PASS ({STEP}/{STEP})")
    print("=" * 60)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())

