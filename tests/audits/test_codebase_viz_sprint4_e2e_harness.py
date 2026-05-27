"""Pytest wrapper for CodebaseVizSprint4E2E.harness (CI mirror)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "audits" / "CodebaseVizSprint4E2E.harness.py"


def test_sprint4_e2e_harness_passes():
    proc = subprocess.run(
        [sys.executable, str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
        check=False,
    )
    assert proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
