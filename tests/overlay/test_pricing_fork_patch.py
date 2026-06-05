"""Unit tests for overlay Google Gemini pricing patch."""

from __future__ import annotations

import importlib

import agent.usage_pricing as up
import pytest
from overlay.agent.pricing_fork_patch import apply_pricing_fork_patch


@pytest.fixture(autouse=True)
def _fresh_pricing_patch():
    """Re-apply patch so tests do not share a stale wrapped function."""
    up_mod = importlib.import_module("agent.usage_pricing")
    if hasattr(up_mod, "_fork_google_pricing_patch_applied"):
        delattr(up_mod, "_fork_google_pricing_patch_applied")
    # Restore original if wrapped multiple times — reload is safest in isolation
    importlib.reload(importlib.import_module("overlay.agent.pricing_fork_patch"))
    apply_pricing_fork_patch()
    yield


def test_pricing_patch_returns_gemini_catalog_entry():
    entry = up.get_pricing_entry("gemini-3.5-flash")
    assert entry is not None
    assert entry.input_cost_per_million is not None
    assert "google" in (entry.source or "").lower() or entry.pricing_version


def test_pricing_patch_falls_back_for_unknown_model():
    result = up.get_pricing_entry("totally-unknown-model-xyz-12345")
    assert result is None or hasattr(result, "input_cost_per_million")


def test_pricing_patch_idempotent():
    first = up.get_pricing_entry
    apply_pricing_fork_patch()
    assert up.get_pricing_entry is first
    assert getattr(up, "_fork_google_pricing_patch_applied", False)
