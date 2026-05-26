#!/usr/bin/env python3
"""E2E: institutioneel hardening — QuickFix flow, common module, guard-log, legal pytest.

Geen live netwerk. Draai: audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] H{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] H{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8", errors="replace")


def _ps(script_path: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(REPO))


def _run_guard(strict: bool = False, quiet: bool = True) -> subprocess.CompletedProcess:
    guard = REPO / "windows/scripts/guard_git_clean.ps1"
    args = ["-RepoRoot", str(REPO)]
    if strict:
        args.append("-Strict")
    if quiet:
        args.append("-Quiet")
    return _ps(guard, *args, timeout=60)


def _run_quickfix() -> subprocess.CompletedProcess:
    qf = REPO / "windows/scripts/quick_fix_repo_hygiene.ps1"
    return _ps(qf, "-RepoRoot", str(REPO), "-NonInteractive", timeout=120)


def _cleanup_test_artifacts() -> None:
    for name in (
        "_test_e2e_qf_script.py",
        "_test_e2e_qf_data.xml",
        "_test_e2e_health_strict.py",
    ):
        p = REPO / name
        if p.is_file():
            p.unlink(missing_ok=True)
    scripts_dir = REPO / "output/research/scripts"
    if scripts_dir.is_dir():
        for p in scripts_dir.glob("_test_e2e_qf_script*.py"):
            p.unlink(missing_ok=True)
    data_dir = REPO / "output/research/data"
    if data_dir.is_dir():
        for p in data_dir.glob("_test_e2e_qf_data*.xml"):
            p.unlink(missing_ok=True)


def test_h1_common_module() -> None:
    common = REPO / "windows/scripts/RepoHygieneCommon.ps1"
    guard_txt = _read("windows/scripts/guard_git_clean.ps1")
    qf_txt = _read("windows/scripts/quick_fix_repo_hygiene.ps1")
    ok = (
        common.is_file()
        and "RepoHygieneCommon.ps1" in guard_txt
        and "Get-HermesRepoRootAllowlist" in guard_txt
        and "RepoHygieneCommon.ps1" in qf_txt
        and "Get-QuickFixDestinationDir" in qf_txt
    )
    _step("RepoHygieneCommon gedeeld", ok)


def test_h2_allowlist_parity() -> None:
    common = _read("windows/scripts/RepoHygieneCommon.ps1")
    guard = _read("windows/scripts/guard_git_clean.ps1")
    ok = "README.md" in common and "Get-HermesRepoRootAllowlist" in guard and "Resolve-HermesAgentRepoRoot" in guard
    _step("allowlist via common module", ok)


def test_h3_quickfix_moves_py() -> None:
    dirty = REPO / "_test_e2e_qf_script.py"
    dirty.write_text("# e2e quickfix\n", encoding="utf-8")
    try:
        proc = _run_quickfix()
        dest_dir = REPO / "output/research/scripts"
        moved = list(dest_dir.glob("_test_e2e_qf_script*.py"))
        ok = proc.returncode == 0 and not dirty.exists() and len(moved) >= 1
        _step("QuickFix verplaatst untracked .py", ok, f"exit={proc.returncode} moved={len(moved)}")
    finally:
        for p in (REPO / "output/research/scripts").glob("_test_e2e_qf_script*.py"):
            p.unlink(missing_ok=True)


def test_h4_guard_clean_after_quickfix() -> None:
    proc = _run_guard(quiet=False)
    ok = proc.returncode == 0 and "OK Repo-root schoon" in proc.stdout
    _step("guard schoon na QuickFix", ok, f"exit={proc.returncode}")


def test_h5_quickfix_moves_xml() -> None:
    dirty = REPO / "_test_e2e_qf_data.xml"
    dirty.write_text("<e2e/>\n", encoding="utf-8")
    try:
        proc = _run_quickfix()
        dest_dir = REPO / "output/research/data"
        moved = list(dest_dir.glob("_test_e2e_qf_data*.xml"))
        ok = proc.returncode == 0 and not dirty.exists() and len(moved) >= 1
        _step("QuickFix verplaatst untracked .xml", ok, f"exit={proc.returncode}")
    finally:
        for p in (REPO / "output/research/data").glob("_test_e2e_qf_data*.xml"):
            p.unlink(missing_ok=True)


def test_h6_health_strict_fails() -> None:
    dirty = REPO / "_test_e2e_health_strict.py"
    dirty.write_text("# strict e2e\n", encoding="utf-8")
    try:
        hc = REPO / "windows/scripts/health_check_repo.ps1"
        proc = _ps(hc, "-RepoRoot", str(REPO), "-Strict", timeout=60)
        ok = proc.returncode != 0
        _step("health_check -Strict bij rommel", ok, f"exit={proc.returncode}")
    finally:
        dirty.unlink(missing_ok=True)


def test_h7_upstream_log_hardening() -> None:
    sync = _read("windows/upstream_sync.ps1")
    ok = (
        "Write-RepoHygieneGuardLog" in sync
        and "maxBytes" in sync
        and "Get-Content" in sync
        and "catch" in sync
    )
    _step("upstream guard-log + trim + catch", ok)


def test_h8_guard_log_via_preflight() -> None:
    """Preflight roept guard aan en schrijft windows/_upstream_sync_guard.log."""
    log_path = REPO / "windows/_upstream_sync_guard.log"
    before = log_path.stat().st_size if log_path.is_file() else 0
    sync = REPO / "windows/upstream_sync.ps1"
    proc = _ps(sync, "-Phase", "Preflight", "-RepoRoot", str(REPO), timeout=180)
    after = log_path.stat().st_size if log_path.is_file() else 0
    grew = log_path.is_file() and after > before
    log_ok = False
    if log_path.is_file():
        body = log_path.read_text(encoding="utf-8", errors="replace")
        log_ok = "exit=" in body and "repo=" in body.lower()
    # exit 2 = dirty repo (bijv. uncommitted audits) is OK; guard-log moet wel geschreven zijn
    ok = grew and log_ok and proc.returncode in (0, 2, 3)
    _step("preflight schrijft guard-log", ok, f"exit={proc.returncode} log_bytes={after}")


def test_h9_legal_pytest() -> None:
    tests = [
        "tests/skills/test_rechtspraak_zoeken_skill.py",
        "tests/skills/test_uitspraak_parseren_skill.py",
        "tests/skills/test_web_research_legal_skill.py",
    ]
    cmd = [str(PY), "-m", "pytest", *tests, "-q", "--tb=line"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(REPO))
    ok = proc.returncode == 0 and "passed" in proc.stdout
    _step("legal skills pytest", ok, f"exit={proc.returncode}")


def test_h10_ecli_validation() -> None:
    parse_py = REPO / "skills/legal/uitspraak-parseren/scripts/parse_uitspraak.py"
    spec = importlib.util.spec_from_file_location("parse_uitspraak_e2e", str(parse_py))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    try:
        mod.fetch_ecli("INVALID")
        ok = False
    except ValueError as e:
        ok = "Ongeldig ECLI" in str(e)
    _step("fetch_ecli weigert ongeldig ECLI", ok)


def test_h11_response_limits() -> None:
    rp = _read("skills/legal/rechtspraak-zoeken/scripts/search_rechtspraak.py")
    ws = _read("skills/legal/web-research-legal/scripts/web_search.py")
    ok = "MAX_HTML_BYTES" in rp and "_read_response_text" in rp and "MAX_HTML_BYTES" in ws
    _step("HTTP response size limit in zoekscripts", ok)


def test_h12_docs() -> None:
    ws = _read("docs/WORKSPACE_CONVENTIONS.md")
    ops = _read("docs/INSTITUTIONAL_OPERATIONS.md")
    ok = (
        "output/research/scripts" in ws
        and "QuickFix" in ws
        and "Repo-hygiene" in ops
        and "quick_fix_repo_hygiene.ps1" in ops
    )
    _step("documentatie repo-hygiene", ok)


def test_h13_update_quickfix_bat() -> None:
    bat = _read("windows/UPDATE_HERMES.bat")
    ok = (
        "-QuickFix" in bat
        and "quick_fix_repo_hygiene.ps1" in bat
        and 'set "HERMES_WIN=%~dp0"' in bat
        and "%HERMES_WIN%upstream_sync.ps1" in bat
        and 'if "%~2"==""' in bat
    )
    _step("UPDATE_HERMES -QuickFix keten (shift-safe)", ok)


def test_h14_cleanup_root() -> None:
    _cleanup_test_artifacts()
    proc = _run_guard(quiet=True)
    leftovers = [
        REPO / "_test_e2e_qf_script.py",
        REPO / "_test_e2e_qf_data.xml",
        REPO / "_test_e2e_health_strict.py",
    ]
    ok = proc.returncode == 0 and not any(p.exists() for p in leftovers)
    _step("geen test-artefacten in root", ok)


def main() -> int:
    print("=" * 60)
    print("  Institutioneel hardening E2E")
    print("=" * 60)
    print()

    _cleanup_test_artifacts()
    try:
        test_h1_common_module()
        test_h2_allowlist_parity()
        test_h3_quickfix_moves_py()
        test_h4_guard_clean_after_quickfix()
        test_h5_quickfix_moves_xml()
        test_h6_health_strict_fails()
        test_h7_upstream_log_hardening()
        test_h8_guard_log_via_preflight()
        test_h9_legal_pytest()
        test_h10_ecli_validation()
        test_h11_response_limits()
        test_h12_docs()
        test_h13_update_quickfix_bat()
        test_h14_cleanup_root()
    finally:
        _cleanup_test_artifacts()

    print()
    print("=" * 60)
    if FAILURES == 0:
        print(f"  ALL PASS ({STEP}/{STEP})")
    else:
        print(f"  FAILURES: {FAILURES}/{STEP}", file=sys.stderr)
    print("=" * 60)
    return 1 if FAILURES > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
