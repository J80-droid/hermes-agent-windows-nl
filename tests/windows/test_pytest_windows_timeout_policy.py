"""Guard: Tier A pyproject uses signal; Windows audit helpers use thread."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMON = REPO_ROOT / "windows" / "HermesShellCommon.ps1"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_pyproject_uses_signal_timeout_method() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    addopts_line = next(
        (ln for ln in text.splitlines() if "addopts" in ln and "timeout-method" in ln),
        "",
    )
    assert "--timeout-method=signal" in addopts_line
    assert "--timeout-method=thread" not in addopts_line


def test_pyproject_timeout_not_in_tool_pytest_addopts_only() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    pytest_section = text.split("[tool.pytest.ini_options]", 1)[-1]
    assert "addopts" in pytest_section
    assert "thread" not in pytest_section


def test_hermes_shell_common_audit_pytest_helpers() -> None:
    text = COMMON.read_text(encoding="utf-8")
    assert "function Invoke-HermesAuditPytest" in text
    assert "function Invoke-HermesCondaAuditPytest" in text
    assert "function Get-HermesAuditPytestOverrideArgs" in text
    assert "function Clear-HermesPytestAddoptsForAudit" in text
    assert "--timeout-method=thread" in text


def test_conda_helper_param_binding_order() -> None:
    text = COMMON.read_text(encoding="utf-8")
    idx_remaining = text.index("ValueFromRemainingArguments = $true, Position = 1")
    idx_env = text.index("$EnvName = 'hermes-env'", idx_remaining)
    assert idx_remaining < idx_env


@pytest.mark.parametrize(
    "needle",
    [
        "function Invoke-HermesTierAPostAuditClean",
        "function Invoke-HermesTierASrcClean",
        "git clean -fd -- $rel",
    ],
)
def test_tier_a_hygiene_helpers_present(needle: str) -> None:
    text = COMMON.read_text(encoding="utf-8")
    assert needle in text
