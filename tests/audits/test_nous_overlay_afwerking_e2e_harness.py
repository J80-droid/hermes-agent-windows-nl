"""Unit tests for audits/NousOverlayAfwerkingE2E.harness.py (gemockt, geen subprocess)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "NousOverlayAfwerkingE2E.harness.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("nous_overlay_afwerking_e2e_harness", HARNESS_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_harness_repo_artefacts_exist():
    mod = _load_harness()
    mod.FAILURES = 0
    mod.STEP = 0
    mod.test_e1_deduplicate_line_section_split()
    mod.test_e3_run_audits_trust_and_fork_gates()
    mod.test_e4_sync_trust_runtime_retry()
    mod.test_e8_enforce_legal_seed_guard()
    assert mod.FAILURES == 0


def test_harness_main_returns_zero_when_all_pass(monkeypatch):
    mod = _load_harness()
    for name in (
        "test_e1_deduplicate_line_section_split",
        "test_e2_deduplicate_pytest_subset",
        "test_e3_run_audits_trust_and_fork_gates",
        "test_e4_sync_trust_runtime_retry",
        "test_e5_collect_env_sync_keys_bootstrap",
        "test_e6_bootstrap_overlay_modules",
        "test_e7_overlay_usage_ts",
        "test_e8_enforce_legal_seed_guard",
    ):
        monkeypatch.setattr(mod, name, lambda: None)
    assert mod.main() == 0
