"""Unit tests for audits/PytestRunnerHardeningE2E.harness.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "PytestRunnerHardeningE2E.harness.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("pytest_runner_hardening_e2e", HARNESS_PATH)
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


def test_e1_fails_when_build_name_still_present(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda _rel: "function Build-HermesPytestArgsFromConfig",
    )
    harness.test_e1_get_pytest_args_function_present()
    assert harness.FAILURES == 1


def test_e1_passes_with_get_name(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda _rel: "function Get-HermesPytestArgsFromConfig",
    )
    harness.test_e1_get_pytest_args_function_present()
    assert harness.FAILURES == 0


def test_e5_fails_without_global_lastexitcode(harness, monkeypatch):
    monkeypatch.setattr(harness, "_read", lambda _rel: "exit $LASTEXITCODE")
    harness.test_e5_fork_gate_runner_global_lastexitcode()
    assert harness.FAILURES == 1


def test_e8_passes_drift_export_fork_section(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda rel: (REPO / rel).read_text(encoding="utf-8"),
    )
    harness.test_e8_drift_baseline_fork_intentional_section()
    assert harness.FAILURES == 0
