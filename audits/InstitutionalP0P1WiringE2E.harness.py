#!/usr/bin/env python3
"""E2E harness: institutional P0+P1 wiring (geen live ingest/chat/API).

E1  Artefacten (bat + rooktest scripts)
E2  institutional_p0_p1_wiring.check (Python parity)
E3  _resolve_hermes_repo for /f trim (geen set /p voor pointer)
E4  Rooktest bat valideert pyproject + search script
E5  guard_forbidden_packages importeerbaar
E6  expand_cli_toolset_arg mcp sentinel
"""

from __future__ import annotations

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
        print(f"[OK] E{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def main() -> int:
    from scripts.institutional_p0_p1_wiring import check_institutional_p0_p1_wiring

    report = check_institutional_p0_p1_wiring(REPO_ROOT)
    for check in report["checks"]:
        _step(check["name"], check["ok"], check.get("detail", ""))

    resolve = REPO_ROOT / "windows" / "scripts" / "rag" / "_resolve_hermes_repo.bat"
    text = resolve.read_text(encoding="utf-8") if resolve.is_file() else ""
    _step("resolve_for_f_trim", "for /f" in text and "set /p HERMES_REPO" not in text)

    rook = REPO_ROOT / "windows" / "scripts" / "user_data" / "hermes_legal_rooktest.bat"
    rook_text = rook.read_text(encoding="utf-8") if rook.is_file() else ""
    _step("rooktest_pyproject_guard", "pyproject.toml" in rook_text and "_rooktest_search.py" in rook_text)

    try:
        from scripts.guard_forbidden_packages import run_guard

        g = run_guard(sys.executable, fix=False)
        _step("guard_forbidden_packages", isinstance(g, dict))
    except Exception as exc:
        _step("guard_forbidden_packages", False, str(exc))

    try:
        from hermes_cli.tools_config import expand_cli_toolset_arg

        out = expand_cli_toolset_arg(["mcp", "file"], {"mcp_servers": {"lancedb-legal": {}}})
        _step("expand_mcp_sentinel", "lancedb-legal" in out and "mcp" not in out)
    except Exception as exc:
        _step("expand_mcp_sentinel", False, str(exc))

    if FAILURES:
        print(f"\nInstitutionalP0P1WiringE2E: {FAILURES} failure(s)", file=sys.stderr)
        return 1
    print("\nInstitutionalP0P1WiringE2E: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
