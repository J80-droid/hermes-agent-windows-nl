"""Legal Windows PS1: parsebaarheid en param()-volgorde (PSES/launcher-contract)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

LEGAL_PS1 = [
    "windows/audits/RUN_LEGAL_DOMAIN_E2E.ps1",
    "windows/scripts/verify_legal_runtime.ps1",
    "windows/scripts/ensure_legal_active_matters.ps1",
    "windows/scripts/sync_legal_lens_from_taxonomy.ps1",
    "windows/scripts/show_legal_ingest_dashboard.ps1",
]

# Launchers met parameters: param() moet vóór eerste dot-source staan.
PARAM_LAUNCHERS = [
    REPO / "windows/audits/RUN_LEGAL_DOMAIN_E2E.ps1",
]


def _parse_ps1(path: Path) -> None:
    ps = (
        f"$e=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile("
        f"'{path}', [ref]$null, [ref]$e); if ($e) {{ $e | ForEach-Object {{ $_.ToString() }}; exit 1 }}"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, f"{path} parse errors:\n{proc.stdout}\n{proc.stderr}"


@pytest.mark.parametrize("rel", LEGAL_PS1)
def test_legal_ps1_parses(rel: str) -> None:
    path = REPO / rel
    assert path.is_file(), rel
    _parse_ps1(path)


def _first_executable_line(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        return s
    return ""


@pytest.mark.parametrize("path", PARAM_LAUNCHERS, ids=lambda p: p.name)
def test_param_before_dot_source(path: Path) -> None:
    """Voorkomt RUN_LEGAL_DOMAIN_E2E-param-fout bij -File (dot-source vóór param)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    seen_dot_source = False
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("param("):
            assert not seen_dot_source, f"{path.name}: param() na dot-source"
            return
        if re.match(r"^\.\s*\(", s):
            seen_dot_source = True
    pytest.fail(f"{path.name}: geen param()-blok gevonden")


def test_legal_domain_e2e_bat_invokes_ps1() -> None:
    bat = (REPO / "windows/audits/RUN_LEGAL_DOMAIN_E2E.bat").read_text(encoding="utf-8")
    assert "RUN_LEGAL_DOMAIN_E2E.ps1" in bat
    assert "-ExecutionPolicy Bypass" in bat
