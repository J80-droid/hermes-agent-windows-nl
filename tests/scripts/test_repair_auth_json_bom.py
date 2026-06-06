"""Tests for scripts/repair_auth_json_bom.py CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_script(env: dict | None = None) -> subprocess.CompletedProcess[str]:
    repo = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "repair_auth_json_bom.py")],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_main_reports_no_bom_on_clean_tree(tmp_path, monkeypatch):
    import os

    root = tmp_path / "hermes"
    prof = root / "profiles" / "legal"
    prof.mkdir(parents=True)
    (prof / "auth.json").write_text('{"active_provider": "nous"}', encoding="utf-8")
    env = os.environ.copy()
    env["HERMES_HOME"] = str(prof)
    env["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
    proc = _run_script(env)
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert "Geen auth.json met UTF-8 BOM" in out


def test_main_repairs_bom_and_lists_paths(tmp_path):
    import os

    root = tmp_path / "hermes"
    prof = root / "profiles" / "legal"
    prof.mkdir(parents=True)
    auth = prof / "auth.json"
    auth.write_bytes(b"\xef\xbb\xbf" + json.dumps({"active_provider": "venice"}).encode())
    env = os.environ.copy()
    env["HERMES_HOME"] = str(prof)
    env["HERMES_WIN_PREFER_LOCALAPPDATA"] = "0"
    proc = _run_script(env)
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert "BOM verwijderd" in out
    assert "legal" in out.replace("\\", "/")
    assert not auth.read_bytes().startswith(b"\xef\xbb\xbf")
