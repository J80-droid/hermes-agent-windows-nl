"""Guard: Tier A pyproject uses signal; Windows audit helpers use thread."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_uses_signal_timeout_method() -> None:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "--timeout-method=signal" in text
    assert "--timeout-method=thread" not in text


def test_hermes_shell_common_audit_pytest_helpers() -> None:
    text = (REPO_ROOT / "windows" / "HermesShellCommon.ps1").read_text(encoding="utf-8")
    assert "function Invoke-HermesAuditPytest" in text
    assert "function Get-HermesAuditPytestOverrideArgs" in text
    assert "--timeout-method=thread" in text
