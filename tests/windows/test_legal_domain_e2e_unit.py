"""pytest: LegalDomainE2E.Unit.Tests.ps1 (geïsoleerde paden, geen volledige machine-E2E)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
UNIT_PS1 = REPO / "windows/tests/LegalDomainE2E.Unit.Tests.ps1"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell unit")
def test_legal_domain_e2e_unit_ps1_passes() -> None:
    assert UNIT_PS1.is_file()
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(UNIT_PS1),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, out[-2000:]
