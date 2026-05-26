"""Pytest-poort voor repo-hygiene / institutional hardening (Windows + PowerShell).

De scenario's leven in ``audits/*E2E.harness.py`` (subprocess + echte guard/quick_fix).
Operators draaien dezelfde logica via ``audits/RUN_*_E2E.bat``.

Piramide:
  - Unit: ``tests/skills/test_*_legal*.py`` (101 tests, gemockte HTTP)
  - Unit: ``tests/audits/test_creative_domain_e2e_harness.py`` (creative E2E-harness, mocks)
  - Integratie (hier): harness via pytest — guard, QuickFix, preflight-log
  - Geen Pester: één stack (pytest), minder drift tussen PS1 en testframework
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
AUDITS = REPO / "audits"

pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Repo-hygiene E2E vereist PowerShell op Windows",
)


def _run_harness(rel: str, *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    script = AUDITS / rel
    assert script.is_file(), f"Harness ontbreekt: {rel}"
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.mark.e2e
def test_repo_hygiene_e2e_harness() -> None:
    """audits/RepoHygieneE2E.harness.py — guard, gitignore, legal imports (9 stappen)."""
    proc = _run_harness("RepoHygieneE2E.harness.py", timeout=120)
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]


@pytest.mark.e2e
def test_update_hermes_integration_e2e_harness() -> None:
    """audits/UpdateHermesIntegrationE2E.harness.py — UPDATE/health_check wiring (10 stappen)."""
    proc = _run_harness("UpdateHermesIntegrationE2E.harness.py", timeout=120)
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]


@pytest.mark.e2e
def test_institutional_hardening_e2e_harness() -> None:
    """audits/InstitutionalHardeningE2E.harness.py — geïntegreerde poort H1–H14."""
    proc = _run_harness("InstitutionalHardeningE2E.harness.py", timeout=300)
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]


@pytest.mark.e2e
def test_creative_domain_e2e_harness() -> None:
    """audits/CreativeDomainE2E.harness.py — creative profiel C1–C11."""
    proc = _run_harness("CreativeDomainE2E.harness.py", timeout=180)
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]


def test_update_hermes_bat_quickfix_shift_safe() -> None:
    """Regressie: shift na -QuickFix mag %%~dp0 niet breken (HERMES_WIN vastzetten)."""
    bat = (REPO / "windows/UPDATE_HERMES.bat").read_text(encoding="utf-8")
    assert 'set "HERMES_WIN=%~dp0"' in bat
    assert "%HERMES_WIN%upstream_sync.ps1" in bat
    assert 'if "%~2"==""' in bat
    assert "Alleen QuickFix" in bat


def test_guard_and_quickfix_scripts_exist() -> None:
    assert (REPO / "windows/scripts/guard_git_clean.ps1").is_file()
    assert (REPO / "windows/scripts/quick_fix_repo_hygiene.ps1").is_file()
    assert (REPO / "windows/scripts/RepoHygieneCommon.ps1").is_file()
