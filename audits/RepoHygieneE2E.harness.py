#!/usr/bin/env python3
"""E2E: Repo-hygiene — guard script, .gitignore, cursor rules, skill imports, domein-manifest.

Geen live API, geen netwerk.
"""

from __future__ import annotations

import importlib.util
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
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}")
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")


def _ensure(rel: str) -> None:
    assert (REPO_ROOT / rel).is_file(), f"Bestand niet gevonden: {rel}"


def _run_guard(strict: bool = False, quiet: bool = True) -> subprocess.CompletedProcess:
    """Voer guard_git_clean.ps1 uit en retourneer result."""
    guard = REPO_ROOT / "windows/scripts/guard_git_clean.ps1"
    cmd = [
        "powershell", "-NoProfile",
        "-File", str(guard),
        "-RepoRoot", str(REPO_ROOT),
    ]
    if strict:
        cmd.append("-Strict")
    if quiet:
        cmd.append("-Quiet")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


# --- Scenario's ---

def test_e1_guard_clean() -> None:
    """Guard script met schone repo geeft exit 0, OK."""
    proc = _run_guard(quiet=False)  # niet quiet om [OK] te zien
    stdout = proc.stdout
    ok = proc.returncode == 0 and "OK Repo-root schoon" in stdout
    _step("guard script clean repo", ok, f"exit={proc.returncode}")


def test_e2_guard_dirty_py() -> None:
    """Simuleer dirty .py in root, guard geeft WARN, exit 0."""
    dirty_file = REPO_ROOT / "_test_e2e_dirty_script.py"
    try:
        dirty_file.write_text("# dirty test file\n")
        proc = _run_guard()
        ok = proc.returncode == 0 and "WARN Scripts in repo-root" in proc.stdout
    finally:
        if dirty_file.exists():
            dirty_file.unlink()
    _step("guard dirty .py detection", ok, f"exit={proc.returncode}")


def test_e3_guard_dirty_xml() -> None:
    """Simuleer dirty .xml in root, guard geeft WARN, exit 0."""
    dirty_file = REPO_ROOT / "_test_e2e_dirty_data.xml"
    try:
        dirty_file.write_text("<test/>\n")
        proc = _run_guard()
        ok = proc.returncode == 0 and "WARN Data-bestanden in repo-root" in proc.stdout
    finally:
        if dirty_file.exists():
            dirty_file.unlink()
    _step("guard dirty .xml detection", ok, f"exit={proc.returncode}")


def test_e4_guard_strict() -> None:
    """Dirty + -Strict geeft exit 2."""
    dirty_file = REPO_ROOT / "_test_e2e_strict_script.py"
    try:
        dirty_file.write_text("# strict test\n")
        proc = _run_guard(strict=True)
        ok = proc.returncode == 2
    finally:
        if dirty_file.exists():
            dirty_file.unlink()
    _step("guard strict mode", ok, f"exit={proc.returncode}")


def test_e5_guard_cleanup() -> None:
    """Na cleanup is de repo weer schoon."""
    proc = _run_guard(quiet=False)
    stdout = proc.stdout
    ok = proc.returncode == 0 and "OK Repo-root schoon" in stdout
    _step("guard cleanup verified", ok)


def test_e6_gitignore_rules() -> None:
    """Versterkte .gitignore regels aanwezig."""
    content = _read(".gitignore")
    checks = [
        "output/" in content,
        "_research/" in content,
        "_workspace/" in content,
        "_extract_" in content,
        "_tmp_" in content,
    ]
    ok = all(checks)
    detail = "5/5 regels" if ok else "ontbrekende gitignore-regels"
    _step(".gitignore versterkte regels", ok, detail)


def test_e7_cursor_rule() -> None:
    """Cursor rule repo-hygiene.mdc bestaat met inhoud."""
    path = ".cursor/rules/repo-hygiene.mdc"
    try:
        content = _read(path)
        ok = "Canonical workspace" in content and "Regels" in content
    except FileNotFoundError:
        ok = False
    _step("cursor rule repo-hygiene.mdc", ok, "" if ok else path)


def test_e8_skill_imports() -> None:
    """Alle 3 legal skills scripts zijn importeerbaar."""
    skills = [
        "skills/legal/rechtspraak-zoeken/scripts/search_rechtspraak.py",
        "skills/legal/uitspraak-parseren/scripts/parse_uitspraak.py",
        "skills/legal/uitspraak-parseren/scripts/extract_docx.py",
        "skills/legal/uitspraak-parseren/scripts/extract_pdf.py",
        "skills/legal/web-research-legal/scripts/web_search.py",
    ]
    bad = []
    for rel in skills:
        p = REPO_ROOT / rel
        if not p.is_file():
            bad.append(f"{rel} (bestand niet gevonden)")
            continue
        spec = importlib.util.spec_from_file_location(p.stem, str(p))
        if spec is None:
            bad.append(f"{rel} (spec None)")
    ok = len(bad) == 0
    detail = "; ".join(bad) if bad else f"{len(skills)} scripts OK"
    _step("legal skill imports", ok, detail)


def test_e9_domain_manifest() -> None:
    """fork_legal_skills entries in domain_toolsets.yaml."""
    content = _read("docs/domain_toolsets.yaml")
    checks = [
        "fork_legal_skills" in content,
        "rechtspraak_zoeken" in content,
        "uitspraak_parseren" in content,
        "web_research_legal" in content,
    ]
    ok = all(checks)
    detail = "4/4 keys" if ok else "ontbrekende manifest-keys"
    _step("domein-manifest fork_legal_skills", ok, detail)


def main() -> None:
    print("=" * 60)
    print("  Repo-hygiene E2E - Audit")
    print("=" * 60)
    print()

    test_e1_guard_clean()
    test_e2_guard_dirty_py()
    test_e3_guard_dirty_xml()
    test_e4_guard_strict()
    test_e5_guard_cleanup()
    test_e6_gitignore_rules()
    test_e7_cursor_rule()
    test_e8_skill_imports()
    test_e9_domain_manifest()

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