#!/usr/bin/env python3
"""E2E: TERMINAL_CWD / MESSAGING_CWD migratie naar config.yaml terminal.cwd.

Geen live gateway, geen mutatie van de echte %LOCALAPPDATA%\\hermes installatie.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
FAILURES = 0
STEP = 0

SCRIPT = REPO / "scripts" / "repair_terminal_cwd.py"
PS1 = REPO / "windows/scripts/repair_terminal_cwd.ps1"
REPAIR_ENTRY = REPO / "windows/scripts/repair_console_entry.ps1"


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] T{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] T{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _audit_python() -> str:
    if os.environ.get("HERMES_AUDIT_PYTHON") and Path(os.environ["HERMES_AUDIT_PYTHON"]).is_file():
        return os.environ["HERMES_AUDIT_PYTHON"]
    for candidate in (
        Path(os.environ.get("USERPROFILE", "")) / "miniconda3/envs/hermes-env/python.exe",
        Path(sys.executable),
    ):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _load_repair_module():
    spec = importlib.util.spec_from_file_location("repair_terminal_cwd", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _isolated_profile(workspace: Path) -> tuple[Path, Path, Path]:
    root = Path(tempfile.mkdtemp(prefix="hermes-tcwd-e2e-"))
    home = root / "profiles" / "audit"
    home.mkdir(parents=True)
    cfg = home / "config.yaml"
    cfg.write_text(
        yaml.safe_dump({"terminal": {"backend": "local", "cwd": "."}}, sort_keys=False),
        encoding="utf-8",
    )
    env = home / ".env"
    env.write_text(f"TERMINAL_CWD={workspace}\n", encoding="utf-8")
    return home, cfg, env


def test_t1_repo_artefacts() -> None:
    required = [SCRIPT, PS1, REPAIR_ENTRY]
    missing = [str(p.relative_to(REPO)) for p in required if not p.is_file()]
    wiring = "repair_terminal_cwd.ps1" in REPAIR_ENTRY.read_text(encoding="utf-8")
    _step("repo-artefacten + repair_console_entry wiring", not missing and wiring, ", ".join(missing) or "OK")


def test_t2_migrate_env_to_config() -> None:
    mod = _load_repair_module()
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td) / "project"
        workspace.mkdir()
        home, cfg, env = _isolated_profile(workspace)
        config = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        written: list[tuple[str, str]] = []
        rc = mod.migrate_terminal_cwd(
            config_path=cfg,
            config=config,
            set_config_value_fn=lambda k, v: written.append((k, v)),
        )
        ok = rc == 0 and written and written[0][0] == "terminal.cwd"
        ok = ok and "TERMINAL_CWD=" not in env.read_text(encoding="utf-8")
        _step("migreer TERMINAL_CWD uit .env", ok, f"rc={rc}")


def test_t3_deprecation_warning_suppressed_after_explicit_cwd() -> None:
    from hermes_cli.config import warn_deprecated_cwd_env_vars
    from io import StringIO
    import sys

    explicit = REPO.resolve().as_posix()
    old = sys.stderr
    buf = StringIO()
    sys.stderr = buf
    try:
        os.environ["TERMINAL_CWD"] = str(REPO)
        warn_deprecated_cwd_env_vars(config={"terminal": {"cwd": explicit}})
    finally:
        sys.stderr = old
        os.environ.pop("TERMINAL_CWD", None)
    _step("geen deprecatie-waarschuwing bij expliciete terminal.cwd", "TERMINAL_CWD" not in buf.getvalue())


def test_t4_pytest_unit_subset() -> None:
    py = _audit_python()
    proc = subprocess.run(
        [py, "-m", "pytest", "tests/scripts/test_repair_terminal_cwd.py", "-q", "--tb=short"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    _step("pytest tests/scripts/test_repair_terminal_cwd.py", proc.returncode == 0, proc.stdout[-400:])


def main() -> int:
    print("=== Terminal CWD migration E2E ===", flush=True)
    test_t1_repo_artefacts()
    test_t2_migrate_env_to_config()
    test_t3_deprecation_warning_suppressed_after_explicit_cwd()
    test_t4_pytest_unit_subset()
    if FAILURES:
        print(f"=== TERMINAL CWD MIGRATION E2E: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print("=== TERMINAL CWD MIGRATION E2E: PASS ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
