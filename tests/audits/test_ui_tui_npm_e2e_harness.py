"""Unit tests for audits/UiTuiNpmE2E.harness.py (wiring; live steps gemockt)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "UiTuiNpmE2E.harness.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("ui_tui_npm_e2e_harness", HARNESS_PATH)
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


def test_w1_fails_when_vitestargs_shadowing(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda rel: "function Invoke-HermesUiTuiVitest { $args = @('vitest' }"
        if "HermesUiTuiNpm" in rel
        else "",
    )
    harness.test_w1_module_wiring()
    assert harness.FAILURES == 1


def test_w1_passes_with_correct_wiring(harness, monkeypatch):
    monkeypatch.setattr(harness, "_read", lambda rel: (REPO / rel).read_text(encoding="utf-8"))
    harness.test_w1_module_wiring()
    assert harness.FAILURES == 0


def test_w5_fails_when_npm_before_drift(harness, monkeypatch):
    monkeypatch.setattr(
        harness,
        "_read",
        lambda rel: "npm ci workspace\nNous Tier A drift gate" if "fork-windows" in rel else "",
    )
    harness.test_w5_ci_npm_after_drift()
    assert harness.FAILURES == 1


def test_w7_live_skip_exit_2(harness, monkeypatch):
    proc = MagicMock(returncode=2, stdout="", stderr="")
    monkeypatch.setattr(harness, "_powershell", lambda *a, **k: proc)
    harness.test_w7_live_vitest_ready()
    assert harness.FAILURES == 0


def test_w7_live_fail_exit_3(harness, monkeypatch):
    proc = MagicMock(returncode=3, stdout="err", stderr="")
    monkeypatch.setattr(harness, "_powershell", lambda *a, **k: proc)
    harness.test_w7_live_vitest_ready()
    assert harness.FAILURES == 1


def test_w8_live_deps_skip(harness, monkeypatch):
    proc = MagicMock(returncode=2, stdout="", stderr="")
    monkeypatch.setattr(harness, "_powershell", lambda *a, **k: proc)
    harness.test_w8_live_deps_only_no_tests()
    assert harness.FAILURES == 0


def test_main_returns_zero_when_all_pass(harness, monkeypatch):
    monkeypatch.setattr(harness, "test_w1_module_wiring", lambda: None)
    monkeypatch.setattr(harness, "test_w2_workspace_vitest_paths", lambda: None)
    monkeypatch.setattr(harness, "test_w3_return_codes_documented", lambda: None)
    monkeypatch.setattr(harness, "test_w4_nous_overlay_integration", lambda: None)
    monkeypatch.setattr(harness, "test_w5_ci_npm_after_drift", lambda: None)
    monkeypatch.setattr(harness, "test_w6_clean_audit_reports", lambda: None)
    monkeypatch.setattr(harness, "test_w7_live_vitest_ready", lambda: None)
    monkeypatch.setattr(harness, "test_w8_live_deps_only_no_tests", lambda: None)
    monkeypatch.setattr(harness, "test_w9_root_package_workspaces", lambda: None)
    assert harness.main() == 0
