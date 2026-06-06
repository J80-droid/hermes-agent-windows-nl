"""Wiring checks for windows/scripts/institutional_p0_p1.bat (no live ingest/chat)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_SCRIPTS = REPO_ROOT / "windows" / "scripts"
INST_BAT = WINDOWS_SCRIPTS / "institutional_p0_p1.bat"
ROOK_BAT = WINDOWS_SCRIPTS / "user_data" / "hermes_legal_rooktest.bat"
RESOLVE_BAT = WINDOWS_SCRIPTS / "rag" / "_resolve_hermes_repo.bat"


def resolve_hermes_repo_from_env() -> Path | None:
    """Mirror _resolve_hermes_repo.bat logic in Python for tests/harness."""
    env_repo = os.environ.get("HERMES_REPO", "").strip()
    if env_repo:
        candidate = Path(env_repo)
        if (candidate / "pyproject.toml").is_file():
            return candidate.resolve()
    rel = (WINDOWS_SCRIPTS / "rag" / ".." / ".." / "..").resolve()
    if (rel / "pyproject.toml").is_file():
        return rel
    pointer = Path.home() / "data" / "hermes_agent_repo.txt"
    if pointer.is_file():
        line = pointer.read_text(encoding="utf-8").splitlines()[0].strip()
        if line:
            candidate = Path(line)
            if (candidate / "pyproject.toml").is_file():
                return candidate.resolve()
    return None


def check_institutional_p0_p1_wiring(repo_root: Path | None = None) -> dict[str, Any]:
    """Return {ok: bool, checks: list[dict]} without subprocess side effects."""
    root = (repo_root or REPO_ROOT).resolve()
    checks: list[dict[str, Any]] = []

    def _add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    _add("institutional_bat", INST_BAT.is_file(), str(INST_BAT))
    _add("rooktest_bat", ROOK_BAT.is_file(), str(ROOK_BAT))
    _add("resolve_bat", RESOLVE_BAT.is_file(), str(RESOLVE_BAT))

    inst_text = INST_BAT.read_text(encoding="utf-8") if INST_BAT.is_file() else ""
    _add(
        "institutional_uses_inst_script_dir_rooktest",
        "ROOKTEST_BAT=%INST_SCRIPT_DIR%user_data" in inst_text,
        "ROOKTEST_BAT via INST_SCRIPT_DIR",
    )
    _add(
        "institutional_passes_hermes_repo",
        'set "HERMES_REPO=%HERMES_REPO%"' in inst_text,
        "explicit HERMES_REPO forward",
    )

    resolve_text = RESOLVE_BAT.read_text(encoding="utf-8") if RESOLVE_BAT.is_file() else ""
    _add(
        "resolve_trims_repo_pointer",
        "for /f" in resolve_text and "hermes_agent_repo.txt" in resolve_text,
        "for /f i.p.v. set /p",
    )

    rook_text = ROOK_BAT.read_text(encoding="utf-8") if ROOK_BAT.is_file() else ""
    _add("rooktest_validates_pyproject", "pyproject.toml" in rook_text, "HERMES_REPO guard")
    _add(
        "rooktest_search_script",
        (root / "scripts" / "rag_pipeline" / "_rooktest_search.py").is_file(),
        str(root / "scripts" / "rag_pipeline" / "_rooktest_search.py"),
    )
    _add(
        "rooktest_chat_script",
        (root / "scripts" / "rag_pipeline" / "_rooktest_chat.py").is_file(),
        str(root / "scripts" / "rag_pipeline" / "_rooktest_chat.py"),
    )

    resolved = resolve_hermes_repo_from_env()
    _add("resolve_hermes_repo", resolved is not None and resolved == root, str(resolved or ""))

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks, "repo_root": str(root)}


def main() -> int:
    report = check_institutional_p0_p1_wiring()
    for check in report["checks"]:
        mark = "OK" if check["ok"] else "FAIL"
        suffix = f" — {check['detail']}" if check.get("detail") else ""
        print(f"[{mark}] {check['name']}{suffix}")
    if report["ok"]:
        print("InstitutionalP0P1Wiring: ALL PASS")
        return 0
    print("InstitutionalP0P1Wiring: FAILURES", file=__import__("sys").stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
