"""Validate windows/tests/pytest_fork_gate.yaml (SSOT for fork pytest gate)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "windows" / "tests" / "pytest_fork_gate.yaml"
LOADER = REPO / "windows" / "scripts" / "load_pytest_fork_gate.py"


def test_manifest_file_exists_and_parses() -> None:
    assert MANIFEST.is_file()
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["paths"]
    assert "tests/overlay/" in data["paths"]


def test_gate_paths_exist_on_disk() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for rel in data["paths"]:
        file_part = rel.split("::", 1)[0].rstrip("/")
        p = REPO / file_part
        if rel.endswith("/"):
            assert p.is_dir(), rel
        else:
            assert p.is_file(), rel


def test_loader_gate_mode_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(LOADER), "--mode", "gate", "--repo-root", str(REPO)],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "gate"
    assert payload["paths"]


def test_loader_upstream_mode() -> None:
    proc = subprocess.run(
        [sys.executable, str(LOADER), "--mode", "upstream", "--repo-root", str(REPO)],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "upstream"
    assert payload["maxfail"] >= 1
    assert payload["junit"]
