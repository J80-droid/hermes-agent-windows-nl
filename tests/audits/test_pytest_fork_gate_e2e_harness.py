"""Unit tests for audits/PytestForkGateE2E.harness.py (gemockt waar nodig)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "PytestForkGateE2E.harness.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("pytest_fork_gate_e2e_harness", HARNESS_PATH)
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


def test_e2_fails_on_loader_nonzero(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_run_loader",
        lambda *_a, **_k: SimpleNamespace(returncode=1, stdout="", stderr="boom"),
    )
    harness.test_e2_loader_gate_mode_json()
    assert harness.FAILURES == 1


def test_e2_passes_with_valid_json(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_run_loader",
        lambda *_a, **_k: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"mode": "gate", "paths": ["tests/x.py"], "markers": "not e2e"}),
            stderr="",
        ),
    )
    harness.test_e2_loader_gate_mode_json()
    assert harness.FAILURES == 0


def test_e6_fails_when_legacy_steps_present(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda _rel: "Invoke-Step 'pytest-overlay' { } Invoke-Step 'pytest-fork-gate' { }",
    )
    harness.test_e6_run_audits_preflight_uses_fork_gate()
    assert harness.FAILURES == 1


def test_e6_passes_with_fork_gate_only(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda rel: (REPO / rel).read_text(encoding="utf-8"),
    )
    harness.test_e6_run_audits_preflight_uses_fork_gate()
    assert harness.FAILURES == 0
