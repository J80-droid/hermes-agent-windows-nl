"""Unit tests for audits/PytestAuditEnvE2E.harness.py (gemockt waar subprocess nodig is)."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "PytestAuditEnvE2E.harness.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("pytest_audit_env_e2e_harness", HARNESS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def harness():
    mod = _load_harness()
    mod.FAILURES = 0
    mod.STEP = 0
    return mod


def test_e1_fails_when_pytest_timeout_plugin_in_default(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda _rel: "function Clear-HermesPytestAddoptsForAudit\n"
        "function Get-HermesAuditPytestOverrideArgs\n"
        "if (-not $env:PYTEST_ADDOPTS) { $env:PYTEST_ADDOPTS = '-p pytest_timeout' }",
    )
    harness.test_e1_shell_common_helpers_documented()
    assert harness.FAILURES == 1


def test_e1_passes_with_clean_helpers(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda rel: (REPO / rel).read_text(encoding="utf-8"),
    )
    harness.test_e1_shell_common_helpers_documented()
    assert harness.FAILURES == 0


def test_e2_detects_double_plugin_failure(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_run_pytest",
        lambda *a, **k: SimpleNamespace(
            returncode=4,
            stdout="",
            stderr="Plugin already registered: pytest_timeout",
        ),
    )
    harness.test_e2_double_timeout_plugin_fails_without_clear()
    assert harness.FAILURES == 0


def test_e2_fails_when_bad_env_still_passes(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_run_pytest",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )
    harness.test_e2_double_timeout_plugin_fails_without_clear()
    assert harness.FAILURES == 1


def test_e3_passes_on_collect_zero(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_run_pytest",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="collected", stderr=""),
    )
    harness.test_e3_audit_env_collect_succeeds()
    assert harness.FAILURES == 0


def test_e3_includes_stderr_tail_on_failure(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_run_pytest",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="E   some collection error",
        ),
    )
    harness.test_e3_audit_env_collect_succeeds()
    assert harness.FAILURES == 1


def test_e4_rejects_module_not_found(harness, monkeypatch):
    monkeypatch.setattr(
        harness.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: hermes_cli.profile_mcp_format",
        ),
    )
    harness.test_e4_sync_mcp_check_imports_overlay()
    assert harness.FAILURES == 1


def test_e4_accepts_check_exit_zero(harness, monkeypatch):
    monkeypatch.setattr(
        harness.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="OK", stderr=""),
    )
    harness.test_e4_sync_mcp_check_imports_overlay()
    assert harness.FAILURES == 0


def test_e5_fails_when_bat_missing_path(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda _rel: "call update_knowledge without INST_SCRIPT_DIR",
    )
    harness.test_e5_institutional_p0_p1_update_knowledge_path()
    assert harness.FAILURES == 1


def test_e6_fails_without_clear_in_gate(harness, monkeypatch):
    monkeypatch.setattr(harness, "_read", lambda _rel: "# no clear helper")
    harness.test_e6_production_gate_clears_pytest_addopts()
    assert harness.FAILURES == 1


def test_main_returns_zero_when_all_pass(monkeypatch):
    mod = _load_harness()
    for name in (
        "test_e1_shell_common_helpers_documented",
        "test_e2_double_timeout_plugin_fails_without_clear",
        "test_e3_audit_env_collect_succeeds",
        "test_e4_sync_mcp_check_imports_overlay",
        "test_e5_institutional_p0_p1_update_knowledge_path",
        "test_e6_production_gate_clears_pytest_addopts",
        "test_e7_e2e_cores_use_audit_pytest_helpers",
        "test_e8_hardening_h9_clears_pytest_addopts",
    ):
        monkeypatch.setattr(mod, name, lambda: None)
    assert mod.main() == 0


def test_main_returns_one_on_failure(monkeypatch):
    mod = _load_harness()

    def _fail():
        mod.FAILURES += 1

    monkeypatch.setattr(mod, "test_e1_shell_common_helpers_documented", _fail)
    for name in (
        "test_e2_double_timeout_plugin_fails_without_clear",
        "test_e3_audit_env_collect_succeeds",
        "test_e4_sync_mcp_check_imports_overlay",
        "test_e5_institutional_p0_p1_update_knowledge_path",
        "test_e6_production_gate_clears_pytest_addopts",
        "test_e7_e2e_cores_use_audit_pytest_helpers",
        "test_e8_hardening_h9_clears_pytest_addopts",
    ):
        monkeypatch.setattr(mod, name, lambda: None)
    assert mod.main() == 1
